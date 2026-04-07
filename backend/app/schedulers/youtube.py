import asyncio
import time
from datetime import datetime, timezone
from typing import List

import httpx
from sqlalchemy import select, case
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.loguru_config import logger
from app.database_async import AsyncSessionFactory
from app.models.models import Channel, Platform, Stream, StreamStatus, Video
from app.services.youtube_fetcher import get_videos_details, parse_youtube_stream
from app.services.quota_guard import can_spend, spend, status as quota_status
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


async def sync_youtube_videos_full() -> None:
    from app.config import settings
    from app.services.youtube_sync import (
        sync_channel_videos,
        is_channel_full_sync_completed,
    )

    if not await is_api_available():
        logger.info("API 不可用，跳过全量同步")
        return

    if settings.youtube_full_sync_completed:
        logger.info("全量同步已完成，跳过")
        return

    api_key = await get_api_key()
    if not api_key:
        return

    BATCH_SIZE = 50

    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Channel).where(
                Channel.platform == Platform.YOUTUBE,
                Channel.is_active.is_(True),
                Channel.status != "graduated",
            )
        )
        channels: List[Channel] = result.scalars().all()

    if not channels:
        return

    total_channels = len(channels)
    total_batches = (total_channels + BATCH_SIZE - 1) // BATCH_SIZE
    current_batch = int(time.time()) // 3600 % total_batches

    start_idx = current_batch * BATCH_SIZE
    end_idx = min(start_idx + BATCH_SIZE, total_channels)
    batch_channels = channels[start_idx:end_idx]

    logger.info(
        "全量同步批次 {}/{}，频道 {}-{}，共 {} 个",
        current_batch + 1,
        total_batches,
        start_idx + 1,
        end_idx,
        len(batch_channels),
    )

    completed_count = 0

    for ch in batch_channels:
        try:
            async with AsyncSessionFactory() as session:
                ch_obj = await session.get(Channel, ch.id)
                if not ch_obj:
                    continue

                is_completed = await is_channel_full_sync_completed(
                    session, ch_obj, api_key
                )
                if is_completed:
                    completed_count += 1
                    logger.info(
                        "频道已全量同步: {} ({}/{})",
                        ch_obj.name,
                        completed_count,
                        len(batch_channels),
                    )
                    continue

                await sync_channel_videos(session, ch_obj, api_key, full_refresh=True)
                await session.commit()
                completed_count += 1
                logger.info(
                    "全量同步频道: {} ({}/{})",
                    ch_obj.name,
                    completed_count,
                    len(batch_channels),
                )
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.warning("全量同步错误 channel_id={}: {}", ch.id, e)

    logger.info(
        "批次同步完成! 批次 {}/{}，已处理 {} 个频道",
        current_batch + 1,
        total_batches,
        completed_count,
    )


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




async def _upsert_stream(db: AsyncSession, channel_id: int, parsed: dict, platform) -> None:
    now = datetime.now(timezone.utc)
    
    insert_data = {
        "channel_id": channel_id,
        "platform": platform,
        "video_id": parsed["video_id"],
        "title": parsed.get("title"),
        "status": parsed.get("status"),
        "viewer_count": parsed.get("viewer_count", 0),
        "updated_at": now,
        "peak_viewers": parsed.get("viewer_count", 0) 
    }

    dialect_name = db.bind.dialect.name
    insert_fn = pg_insert if dialect_name == "postgresql" else sqlite_insert

    stmt = insert_fn(Stream).values(**insert_data)

    update_cols = {
        "title": stmt.excluded.title,
        "status": stmt.excluded.status,
        "viewer_count": stmt.excluded.viewer_count,
        "updated_at": now,
        
        "peak_viewers": case(
            (stmt.excluded.viewer_count > Stream.peak_viewers, stmt.excluded.viewer_count),
            else_=Stream.peak_viewers
        )
    }

    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=["channel_id", "video_id"],
        set_=update_cols
    )

    await db.execute(upsert_stmt)