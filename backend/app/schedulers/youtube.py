import asyncio
import time
from typing import List

import httpx
from sqlalchemy import select

from app.loguru_config import logger
from app.database_async import AsyncSessionFactory
from app.models.models import Channel, Platform, Stream, StreamStatus, Video
from app.services.youtube_fetcher import get_videos_details, parse_youtube_stream
from app.services.quota_guard import can_spend, spend, status as quota_status
from app.services.api_key_manager import get_api_key, is_api_available
from app.services.youtube_sync_state import (
    get_incremental_state,
    set_incremental_state,
    get_full_state,
    set_full_completed,
    is_all_full_completed,
    set_all_full_completed,
)
from app.db_utils import upsert_stream
from app.constants import ChannelStatus


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
                        await upsert_stream(
                            db,
                            vid_to_ch_id[parsed["video_id"]],
                            parsed,
                            Platform.YOUTUBE,
                        )

        await db.commit()
        remaining = (await quota_status())["remaining"]
        logger.info("刷新 {} 条 | 配额剩余 {}", len(active), remaining)


async def sync_youtube_videos_incremental() -> None:
    """每天执行一次，对所有频道进行增量同步"""
    from app.services.youtube_sync import sync_channel_videos

    if not await is_api_available():
        logger.info("API 不可用，跳过增量同步")
        return

    api_key = await get_api_key()
    if not api_key:
        return

    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Channel).where(
                Channel.platform == Platform.YOUTUBE,
                Channel.is_active.is_(True),
                Channel.status != ChannelStatus.GRADUATED,
            )
        )
        channels: List[Channel] = result.scalars().all()

    if not channels:
        return

    logger.info("开始增量同步，共 {} 个频道", len(channels))

    for ch in channels:
        try:
            async with AsyncSessionFactory() as session:
                ch_obj = await session.get(Channel, ch.id)
                if not ch_obj:
                    continue

                await sync_channel_videos(session, ch_obj, api_key, full_refresh=False)
                await session.commit()

                result = await session.execute(
                    select(Video).where(Video.channel_id == ch_obj.id)
                )
                video_count = len(result.scalars().all())
                await set_incremental_state(ch_obj.id, video_count)

                logger.info("增量同步完成: {} ({} videos)", ch_obj.name, video_count)
                await asyncio.sleep(0.3)
        except Exception as e:
            logger.warning("增量同步错误 channel_id={}: {}", ch.id, e)

    logger.info("增量同步全部完成")


async def sync_youtube_videos_full() -> None:
    """每批次10个频道进行全量同步，全部完成后停止"""
    from app.services.youtube_sync import sync_channel_videos

    if not await is_api_available():
        logger.info("API 不可用，跳过全量同步")
        return

    if await is_all_full_completed():
        logger.info("所有频道全量同步已完成，跳过")
        return

    api_key = await get_api_key()
    if not api_key:
        return

    BATCH_SIZE = 10

    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Channel).where(
                Channel.platform == Platform.YOUTUBE,
                Channel.is_active.is_(True),
                Channel.status != ChannelStatus.GRADUATED,
            )
        )
        channels: List[Channel] = result.scalars().all()

    if not channels:
        return

    incomplete_channels = [
        ch
        for ch in channels
        if not (await get_full_state(ch.id) or {}).get("completed")
    ]

    if not incomplete_channels:
        logger.info("所有频道已完成全量同步，跳过")
        return

    total_incomplete = len(incomplete_channels)
    total_batches = (total_incomplete + BATCH_SIZE - 1) // BATCH_SIZE
    current_batch = int(time.time()) // 3600 % total_batches

    batch_start = current_batch * BATCH_SIZE
    batch_end = min(batch_start + BATCH_SIZE, total_incomplete)
    batch_channels = incomplete_channels[batch_start:batch_end]

    logger.info(
        "全量同步批次 {}/{}，频道 {}-{}，共 {} 个（剩余未完成: {}）",
        current_batch + 1,
        total_batches,
        batch_start + 1,
        batch_end,
        len(batch_channels),
        total_incomplete,
    )

    completed_count = 0
    newly_completed = 0

    for ch in batch_channels:
        try:
            async with AsyncSessionFactory() as session:
                ch_obj = await session.get(Channel, ch.id)
                if not ch_obj:
                    continue

                full_state = await get_full_state(ch_obj.id)
                if full_state and full_state.get("completed"):
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

                result = await session.execute(
                    select(Video).where(Video.channel_id == ch_obj.id)
                )
                video_count = len(result.scalars().all())
                await set_full_completed(ch_obj.id, video_count)

                completed_count += 1
                newly_completed += 1
                logger.info(
                    "全量同步频道: {} ({}/{})",
                    ch_obj.name,
                    completed_count,
                    len(batch_channels),
                )
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.warning("全量同步错误 channel_id={}: {}", ch.id, e)

    if newly_completed > 0:
        all_completed = True
        for ch in channels:
            full_state = await get_full_state(ch.id)
            if not (full_state and full_state.get("completed")):
                all_completed = False
                break
        if all_completed:
            await set_all_full_completed(True)
            logger.info("所有频道全量同步已完成！")

    logger.info(
        "批次同步完成! 批次 {}/{}，已处理 {} 个频道",
        current_batch + 1,
        total_batches,
        completed_count,
    )


async def reset_all_youtube_sync_states() -> int:
    """重置所有同步状态（用于手动重新开始）"""
    from app.services.youtube_sync_state import clear_all_sync_states

    deleted = await clear_all_sync_states()
    await set_all_full_completed(False)
    logger.info("已重置所有 YouTube 同步状态")
    return deleted


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
                await upsert_stream(
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
