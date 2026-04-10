from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select

from app.loguru_config import logger
from app.crud.session import session_scope
from app.crud import ChannelRepository, StreamRepository, VideoRepository
from app.models.models import Channel, Platform
from app.services.bilibili_live import get_rooms_by_uids, parse_bilibili_room
from app.services.youtube_channel import get_channel_details
from app.services.youtube_sync import sync_channel_videos
from app.services.youtube_websub import subscribe_all_active_channels
from app.services.api_key_manager import get_api_key, is_api_available
from app.services.quota_guard import can_spend, spend, status as quota_status
from app.services.youtube_fetcher import get_videos_details, parse_youtube_stream
from app.db_utils import upsert_stream
from app.config import settings


class BaseTask(ABC):
    """后台任务基类。"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self._last_run: Optional[datetime] = None
        self._run_count: int = 0

    @property
    def last_run(self) -> Optional[datetime]:
        return self._last_run

    @property
    def run_count(self) -> int:
        return self._run_count

    @abstractmethod
    async def execute(self) -> None:
        raise NotImplementedError

    async def run(self) -> bool:
        try:
            logger.info(" task %s start", self.task_id)
            await self.execute()
            self._last_run = datetime.now(timezone.utc)
            self._run_count += 1
            logger.info(
                " task %s completed (run_count=%d)", self.task_id, self._run_count
            )
            return True
        except Exception as e:
            logger.error(" task %s failed: %s", self.task_id, e)
            return False


class IntervalTask(BaseTask):
    def __init__(self, task_id: str, interval_seconds: int):
        super().__init__(task_id)
        self.interval_seconds = interval_seconds

    @property
    def interval(self) -> int:
        return self.interval_seconds


class CronTask(BaseTask):
    def __init__(
        self,
        task_id: str,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
        day_of_week: Optional[str] = None,
    ):
        super().__init__(task_id)
        self.hour = hour
        self.minute = minute
        self.day_of_week = day_of_week


class TaskRegistry:
    _tasks: dict[str, BaseTask] = {}

    @classmethod
    def register(cls, task: BaseTask) -> None:
        cls._tasks[task.task_id] = task

    @classmethod
    def get(cls, task_id: str) -> Optional[BaseTask]:
        return cls._tasks.get(task_id)

    @classmethod
    def get_all(cls) -> dict[str, BaseTask]:
        return cls._tasks.copy()

    @classmethod
    def list_tasks(cls) -> list[str]:
        return list(cls._tasks.keys())


def register_task(task: BaseTask) -> None:
    TaskRegistry.register(task)
    return task


# ── Bilibili Tasks ────────────────────────────────────────────────────────────────


async def update_bilibili_streams() -> None:
    async with session_scope() as session:
        channel_repo = ChannelRepository(session)
        channels = await channel_repo.get_active_channels(Platform.BILIBILI)
        if not channels:
            return
        uid_to_ch_id = {ch.channel_id: ch.id for ch in channels}
        uids = list(uid_to_ch_id.keys())

    rooms_data = await get_rooms_by_uids(uids)

    async with session_scope() as session:
        for uid, room_data in rooms_data.items():
            if uid in uid_to_ch_id:
                parsed = parse_bilibili_room(room_data)
                await upsert_stream(
                    session, uid_to_ch_id[uid], parsed, Platform.BILIBILI
                )
        await session.commit()
        logger.info("更新 %d 个房间", len(rooms_data))


# ── YouTube Tasks ────────────────────────────────────────────────────────────────


async def update_youtube_streams() -> None:
    if not await is_api_available():
        return
    if not await can_spend("videos.list", 1):
        logger.info("配额耗尽，跳过 update_youtube_streams")
        return

    api_key = await get_api_key()

    async with session_scope() as session:
        stream_repo = StreamRepository(session)
        active = await stream_repo.get_live_streams(Platform.YOUTUBE)
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
                            session,
                            vid_to_ch_id[parsed["video_id"]],
                            parsed,
                            Platform.YOUTUBE,
                        )

        await session.commit()
        remaining = (await quota_status())["remaining"]
        logger.info("刷新 %d 条 | 配额剩余 %d", len(active), remaining)


async def sync_youtube_videos_incremental() -> None:
    if not await is_api_available():
        logger.info("API 不可用，跳过增量同步")
        return
    api_key = await get_api_key()
    if not api_key:
        return

    async with session_scope() as session:
        channel_repo = ChannelRepository(session)
        channels = await channel_repo.get_active_channels(Platform.YOUTUBE)

    if not channels:
        return

    logger.info("开始增量同步，共 %d 个频道", len(channels))

    for ch in channels:
        try:
            async with session_scope() as session:
                channel_repo = ChannelRepository(session)
                ch_obj = await channel_repo.get(ch.id)
                if not ch_obj:
                    continue
                await sync_channel_videos(session, ch_obj, api_key, full_refresh=False)
                await session.commit()
                logger.info("增量同步完��: %s", ch_obj.name)
                await asyncio.sleep(0.3)
        except Exception as e:
            logger.warning("增量同步错误 channel_id=%d: %s", ch.id, e)

    logger.info("增量同步全部完成")


async def sync_youtube_videos_full() -> None:
    from app.services.youtube_sync_state import (
        get_full_state,
        set_full_completed,
        is_all_full_completed,
        set_all_full_completed as set_all_completed,
    )

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

    async with session_scope() as session:
        channel_repo = ChannelRepository(session)
        channels = await channel_repo.get_active_channels(Platform.YOUTUBE)

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
        "全量同步批次 %d/%d，频道 %d-%d",
        current_batch + 1,
        total_batches,
        batch_start + 1,
        batch_end,
    )

    completed_count = 0
    for ch in batch_channels:
        try:
            async with session_scope() as session:
                channel_repo = ChannelRepository(session)
                ch_obj = await channel_repo.get(ch.id)
                if not ch_obj:
                    continue
                full_state = await get_full_state(ch_obj.id)
                if full_state and full_state.get("completed"):
                    completed_count += 1
                    continue
                await sync_channel_videos(session, ch_obj, api_key, full_refresh=True)
                await session.commit()
                video_repo = VideoRepository(session)
                videos = await video_repo.get_by_channel(ch_obj.id, limit=10000)
                await set_full_completed(ch_obj.id, len(videos))
                completed_count += 1
                logger.info("全量同步频道: %s", ch_obj.name)
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.warning("全量同步错误 channel_id=%d: %s", ch.id, e)

    all_completed = all(
        (await get_full_state(ch.id) or {}).get("completed") for ch in channels
    )
    if all_completed:
        await set_all_completed(True)
        logger.info("所有频道全量同步已完成！")

    logger.info("批次同步完成! 批次 %d/%d", current_batch + 1, total_batches)


async def discover_live_streams_from_videos() -> None:
    if not await is_api_available():
        return

    async with session_scope() as session:
        channel_repo = ChannelRepository(session)
        channels = await channel_repo.get_active_channels(Platform.YOUTUBE)
        if not channels:
            return
        stream_repo = StreamRepository(session)
        for ch in channels:
            videos = await stream_repo.get_live_and_upcoming(ch.id, limit=10)
            for video in videos:
                await stream_repo.upsert_stream(
                    ch.id,
                    video.video_id,
                    {
                        "video_id": video.video_id,
                        "title": video.title,
                        "thumbnail_url": video.thumbnail_url,
                        "status": video.status,
                        "viewer_count": 0,
                        "platform": Platform.YOUTUBE,
                    },
                )
        await session.commit()


# ── Maintenance Tasks ────────────────────────────────────────────────────────────────


async def refresh_channel_details() -> None:
    if not await is_api_available():
        return

    async with session_scope() as session:
        channel_repo = ChannelRepository(session)
        channels = await channel_repo.get_active_channels(Platform.YOUTUBE)
        if not channels:
            return
        logger.info("开始刷新 %d 个 YouTube 频道", len(channels))
        for ch in channels:
            try:
                details = await get_channel_details(ch.channel_id)
                if details:
                    changed = False
                    if (
                        details.get("banner_url")
                        and ch.banner_url != details["banner_url"]
                    ):
                        ch.banner_url = details["banner_url"]
                        changed = True
                    if (
                        details.get("description")
                        and ch.description != details["description"]
                    ):
                        ch.description = details["description"]
                        changed = True
                    if (
                        details.get("twitter_url")
                        and ch.twitter_url != details["twitter_url"]
                    ):
                        ch.twitter_url = details["twitter_url"]
                        changed = True
                    if (
                        details.get("youtube_url")
                        and ch.youtube_url != details["youtube_url"]
                    ):
                        ch.youtube_url = details["youtube_url"]
                        changed = True
                    if changed:
                        ch.updated_at = datetime.now(timezone.utc)
            except Exception as e:
                logger.warning("%s: %s", ch.name, e)
        await session.commit()
        logger.info("完成")


async def daily_backfill_sync() -> None:
    if not await is_api_available():
        return
    api_key = await get_api_key()
    if not api_key:
        return

    async with session_scope() as session:
        channel_repo = ChannelRepository(session)
        channels = await channel_repo.get_active_channels(Platform.YOUTUBE)

    for ch in channels:
        async with session_scope() as session:
            channel_repo = ChannelRepository(session)
            ch_obj = await channel_repo.get(ch.id)
            if ch_obj:
                await sync_channel_videos(session, ch_obj, api_key, full_refresh=False)


async def renew_websub() -> None:
    callback_url = settings.websub_callback_url
    await subscribe_all_active_channels(callback_url)


async def scheduled_scrape_all() -> None:
    from app.services.scraper.sync import scrape_and_sync_all

    async with session_scope() as session:
        return await scrape_and_sync_all(session)


__all__ = [
    "BaseTask",
    "IntervalTask",
    "CronTask",
    "TaskRegistry",
    "register_task",
    "update_bilibili_streams",
    "update_youtube_streams",
    "sync_youtube_videos_incremental",
    "sync_youtube_videos_full",
    "discover_live_streams_from_videos",
    "refresh_channel_details",
    "daily_backfill_sync",
    "renew_websub",
    "scheduled_scrape_all",
]
