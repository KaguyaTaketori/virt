import time
import asyncio
from datetime import datetime, timezone
from typing import List

import httpx
from sqlalchemy import select

from app.loguru_config import logger
from app.database_async import AsyncSessionFactory
from app.models.models import Channel, Platform, Stream, StreamStatus, Video
from app.services.youtube_fetcher import get_videos_details, parse_youtube_stream
from app.services.quota_guard import can_spend, spend, status as quota_status
from app.services.youtube_sync import sync_channel_videos
from app.services.api_key_manager import get_api_key, is_api_available


async def update_youtube_streams() -> None:
    if not await is_api_available():
        return
    if not await can_spend("videos.list", 1):
        logger.info("配额耗尽，跳过 update_youtube_streams")
        return

    api_key = await get_api_key()

    async with AsyncSessionFactory() as db:
        result = await db.execute(
            select(Stream).where(
                Stream.platform == Platform.YOUTUBE,
                Stream.status.in_([StreamStatus.LIVE, StreamStatus.UPCOMING]),
                Stream.video_id.isnot(None),
            )
        )
        active = result.scalars().all()
        if not active:
            return

        vid_to_ch_id = {s.video_id: s.channel_id for s in active}
        video_ids = list(vid_to_ch_id.keys())

        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(0, len(video_ids), 50):
                chunk = video_ids[i : i + 50]
                if not await can_spend("videos.list", 1):
                    break
                items = await get_videos_details(client, chunk, api_key=api_key)
                await spend("videos.list", 1)
                for item in items:
                    parsed = parse_youtube_stream(item)
                    if parsed and parsed["video_id"] in vid_to_ch_id:
                        await _upsert_stream(
                            db,
                            vid_to_ch_id[parsed["video_id"]],
                            parsed,
                            Platform.YOUTUBE,
                        )

        await db.commit()
        remaining = (await quota_status())["remaining"]
        logger.info("刷新 {} 条 | 配额剩余 {}", len(active), remaining)


async def sync_youtube_videos_bulk(limit: int = 50) -> None:
    if not await is_api_available():
        return

    api_key = await get_api_key()
    if not api_key:
        return

    round_num = int(time.time()) // 3600 % 10

    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Channel).where(
                Channel.platform == Platform.YOUTUBE,
                Channel.is_active.is_(True),
            )
        )
        all_channels: List[Channel] = result.scalars().all()

    if not all_channels:
        return

    total = len(all_channels)
    offset = (round_num * limit) % total
    batch = all_channels[offset : offset + limit]
    if len(batch) < limit:
        batch += all_channels[: limit - len(batch)]

    logger.info(
        "bulk sync: {} channels (round={}, offset={})", len(batch), round_num, offset
    )

    async with AsyncSessionFactory() as session:
        for ch in batch:
            try:
                ch_obj = await session.get(Channel, ch.id)
                if not ch_obj:
                    continue
                await sync_channel_videos(session, ch_obj, api_key, full_refresh=False)
                await session.commit()
                await asyncio.sleep(0.5)
            except Exception as e:
                await session.rollback()
                logger.warning("bulk sync error for channel_id={}: {}", ch.id, e)

    logger.info("bulk sync done: {} channels processed", len(batch))


async def discover_live_streams_from_videos() -> None:
    if not await is_api_available():
        return

    async with AsyncSessionFactory() as db:
        result = await db.execute(
            select(Channel).where(
                Channel.platform == Platform.YOUTUBE,
                Channel.is_active.is_(True),
            )
        )
        channels = result.scalars().all()
        if not channels:
            return

        for ch in channels:
            result = await db.execute(
                select(Video).where(
                    Video.channel_id == ch.id,
                    Video.status.in_(["live", "upcoming"]),
                )
            )
            for video in result.scalars().all():
                await _upsert_stream(
                    db,
                    ch.id,
                    {
                        "video_id": video.video_id,
                        "title": video.title,
                        "thumbnail_url": video.thumbnail_url,
                        "status": video.status,
                        "scheduled_at": video.scheduled_at,
                        "started_at": video.live_started_at,
                        "viewer_count": 0,
                    },
                    Platform.YOUTUBE,
                )

        await db.commit()


async def _upsert_stream(db, channel_id: int, parsed: dict, platform) -> None:
    result = await db.execute(
        select(Stream).where(
            Stream.channel_id == channel_id,
            Stream.video_id == parsed["video_id"],
        )
    )
    stream = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if not stream:
        stream = Stream(channel_id=channel_id, platform=platform)
        db.add(stream)

    for field, value in parsed.items():
        if getattr(stream, field, None) != value:
            setattr(stream, field, value)

    stream.updated_at = now
    if parsed.get("viewer_count", 0) > (stream.peak_viewers or 0):
        stream.peak_viewers = parsed["viewer_count"]
