from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.loguru_config import logger, console
from app.database import session_scope, upsert_stream
from app.repositories import ChannelRepository, StreamRepository
from app.models.models import Channel, Platform
from app.integrations.bili_client import get_bili_client
from app.integrations.youtube import get_youtube_sync_service
from app.integrations.websub.subscription_service import websub_service
from app.services.api_key_manager import get_api_key, is_api_available
from app.deps.permissions import get_quota_dep
from app.services.scraper.sync import scrape_and_sync_all
from app.services.youtube_sync_state import (
    set_full_completed,
    is_all_full_completed,
    set_all_full_completed as set_all_completed,
)
from app.services.redis_client import RedisClient
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn, MofNCompleteColumn


quota_dep = get_quota_dep()


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
            logger.info(" task {} start", self.task_id)
            await self.execute()
            self._last_run = datetime.now(timezone.utc)
            self._run_count += 1
            logger.info(
                " task {} completed (run_count={})", self.task_id, self._run_count
            )
            return True
        except Exception as e:
            logger.error(" task {} failed: {}", self.task_id, e)
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


async def update_bilibili_streams() -> None:
    client = get_bili_client()
    async with session_scope() as session:
        channel_repo = ChannelRepository(session)
        channels = await channel_repo.get_active_channels(Platform.BILIBILI)
        if not channels:
            return
        uid_to_ch_id = {ch.channel_id: ch.id for ch in channels}
        uids = list(uid_to_ch_id.keys())

    rooms_data = await client.batch_get_live_status(uids)

    async with session_scope() as session:
        for uid, room_data in rooms_data.items():
            if uid in uid_to_ch_id and room_data and room_data.status != "offline":
                parsed = {
                    "video_id": room_data.video_id,
                    "title": room_data.title,
                    "thumbnail_url": room_data.thumbnail_url,
                    "status": room_data.status,
                    "viewer_count": room_data.viewer_count,
                    "started_at": room_data.started_at,
                }
                await upsert_stream(
                    session, uid_to_ch_id[uid], parsed, Platform.BILIBILI
                )
        await session.commit()
        logger.info("更新 {} 个房间", len(rooms_data))


async def update_youtube_streams() -> None:
    if not await is_api_available():
        return
    if not await quota_dep.can_spend("videos.list", 1):
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
                if not await quota_dep.can_spend("videos.list", 1):
                    break

                params = {
                    "key": api_key,
                    "part": "snippet,liveStreamingDetails,statistics",
                    "id": ",".join(chunk),
                }
                resp = await client.get(
                    "https://www.googleapis.com/youtube/v3/videos", params=params
                )
                items = resp.json().get("items", [])

                await quota_dep.spend("videos.list", 1)

                for item in items:
                    snippet = item.get("snippet", {})
                    live_details = item.get("liveStreamingDetails", {})
                    life_cycle = snippet.get("liveBroadcastContent", "none")

                    if life_cycle == "none" and not live_details.get("actualStartTime"):
                        continue

                    status_map = {
                        "live": "live",
                        "upcoming": "upcoming",
                        "none": "archive",
                    }
                    concurrent = live_details.get("concurrentViewers")
                    viewer_count = (
                        int(concurrent) if concurrent and concurrent.isdigit() else 0
                    )

                    thumbnails = snippet.get("thumbnails", {})
                    thumbnail_url = (
                        thumbnails.get("maxres", {}).get("url")
                        or thumbnails.get("high", {}).get("url")
                        or thumbnails.get("medium", {}).get("url")
                    )

                    parsed = {
                        "video_id": item["id"],
                        "title": snippet.get("title"),
                        "thumbnail_url": thumbnail_url,
                        "status": status_map.get(life_cycle, "archive"),
                        "viewer_count": viewer_count,
                        "scheduled_at": datetime.fromisoformat(
                            live_details.get("scheduledStartTime", "").replace(
                                "Z", "+00:00"
                            )
                        )
                        if live_details.get("scheduledStartTime")
                        else None,
                        "started_at": datetime.fromisoformat(
                            live_details.get("actualStartTime", "").replace(
                                "Z", "+00:00"
                            )
                        )
                        if live_details.get("actualStartTime")
                        else None,
                    }

                    if parsed["video_id"] in vid_to_ch_id:
                        await upsert_stream(
                            session,
                            vid_to_ch_id[parsed["video_id"]],
                            parsed,
                            Platform.YOUTUBE,
                        )

        await session.commit()
        status = await quota_dep.status()
        logger.info("刷新 {} 条 | 配额剩余 {}", len(active), status["remaining"])


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

    logger.info("开始增量同步，共 {} 个频道", len(channels))

    for ch in channels:
        try:
            async with session_scope() as session:
                channel_repo = ChannelRepository(session)
                ch_obj = await channel_repo.get(ch.id)
                if not ch_obj:
                    continue
                yt_client = get_youtube_sync_service()
                await yt_client.sync_channel_videos(session, ch_obj, api_key)
                await session.commit()
                logger.info("增量同步完成: {}", ch_obj.name)
                await asyncio.sleep(0.3)
        except Exception as e:
            logger.warning("增量同步错误 channel_id={}: {}", ch.id, e)

    logger.info("增量同步全部完成")


async def sync_youtube_videos_full(limit: int = 10) -> None:
    """
    全量同步逻辑：每次执行只同步 limit 个频道。
    """
    if not await is_api_available():
        logger.info("API 不可用，跳过全量同步")
        return
    if await is_all_full_completed():
        logger.info("所有频道全量同步已完成，跳过")
        return
    
    api_key = await get_api_key()
    if not api_key:
        return

    async with session_scope() as session:
        channel_repo = ChannelRepository(session)
        all_channels = await channel_repo.get_active_channels(Platform.YOUTUBE)

    if not all_channels:
        return

    incomplete_channels = await _filter_incomplete_channels(all_channels)

    if not incomplete_channels:
        await set_all_completed(True)
        logger.info("所有频道已完成全量同步")
        return

    total_to_process_this_run = len(incomplete_channels)
    batch_to_run = incomplete_channels[:limit]
    
    logger.info(
        "本次全量同步任务启动: 处理 {} 个频道 (剩余待处理总量: {})", 
        len(batch_to_run), 
        total_to_process_this_run
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        expand=True,
        console=console
    ) as progress:
        main_task = progress.add_task(
            f"[yellow]本次同步进度 (Batch Size: {limit})", 
            total=len(batch_to_run)
        )
        detail_task = progress.add_task("[white]等待中...", total=None)

        for ch in batch_to_run:
            try:
                async with session_scope() as session:
                    channel_repo = ChannelRepository(session)
                    ch_obj = await channel_repo.get(ch.id)
                    if not ch_obj:
                        progress.advance(main_task)
                        continue

                    progress.update(detail_task, description=f"正在同步: {ch_obj.name[:10]}", completed=0)
                    
                    yt_client = get_youtube_sync_service()
                    total_count = await yt_client.sync_channel_videos(
                        session=session,
                        channel=ch_obj,
                        full_refresh=True,
                        progress=progress,
                        task_id=detail_task,
                    )

                    # 标记该频道全量完成
                    await set_full_completed(ch.id, total_count)
                    await session.commit()

                    progress.console.log(f"[green]✓[/green] 完成: {ch_obj.name} (共抓取 {total_count} 视频)")
                    progress.advance(main_task)

                await asyncio.sleep(0.5)
            except Exception as e:
                progress.console.log(f"[red]× 错误[/red] {ch.channel_id}: {e}")
                progress.advance(main_task)
                await asyncio.sleep(2)

    if total_to_process_this_run <= len(batch_to_run):
        await set_all_completed(True)
        logger.info("所有频道全量同步已全部完成")


async def _filter_incomplete_channels(
    channels: list[Channel],
) -> list[Channel]:
    redis = await RedisClient.get_client()
    keys = [f"youtube:sync:full:{ch.id}" for ch in channels]

    raw_values = await redis.mget(*keys)

    incomplete = []
    for ch, raw in zip(channels, raw_values):
        if raw is None:
            incomplete.append(ch)
            continue
        try:
            state = json.loads(raw)
            if not state.get("completed"):
                incomplete.append(ch)
        except json.JSONDecodeError:
            incomplete.append(ch)

    return incomplete


async def discover_live_streams_from_videos() -> None:
    if not await is_api_available():
        logger.info("API 不可用，跳过直播发现")
        return
    if not await quota_dep.can_spend("search.list", 1):
        logger.info("配额不足，跳过直播发现")
        return

    api_key = await get_api_key()

    async with session_scope() as session:
        channel_repo = ChannelRepository(session)
        channels = await channel_repo.get_active_channels(Platform.YOUTUBE)

    if not channels:
        return

    async with httpx.AsyncClient(timeout=30.0) as client:
        for ch in channels:
            params = {
                "key": api_key,
                "part": "id,snippet",
                "channelId": ch.channel_id,
                "eventType": "live",
                "type": "video",
                "maxResults": 5,
            }
            try:
                resp = await client.get(
                    "https://www.googleapis.com/youtube/v3/search", params=params
                )
                if resp.status_code == 403:
                    logger.info("配额耗尽，停止直播发现")
                    break
                items = resp.json().get("items", [])
                if items:
                    for item in items:
                        snippet = item.get("snippet", {})
                        vid = item.get("id", {}).get("videoId")
                        if vid:
                            parsed = {
                                "video_id": vid,
                                "title": snippet.get("title"),
                                "thumbnail_url": snippet.get("thumbnails", {})
                                .get("high", {})
                                .get("url"),
                                "status": "live",
                                "viewer_count": 0,
                            }
                            async with session_scope() as session:
                                await upsert_stream(
                                    session, ch.id, parsed, Platform.YOUTUBE
                                )
                                await session.commit()

                await quota_dep.spend("search.list", 1)
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning("直播发现错误 channel={}: {}", ch.channel_id, e)

    logger.info("直播发现完成")


async def refresh_channel_details() -> None:
    async with session_scope() as session:
        channel_repo = ChannelRepository(session)
        channels = await channel_repo.get_active_channels(Platform.YOUTUBE)

    yt_client = get_youtube_sync_service()
    for ch in channels:
        try:
            info = await yt_client.get_channel_info(ch.channel_id)
            if info:
                async with session_scope() as session:
                    channel_repo = ChannelRepository(session)
                    db_ch = await channel_repo.get(ch.id)
                    if db_ch:
                        db_ch.name = info.get("name", db_ch.name)
                        db_ch.avatar_url = info.get("avatar_url", db_ch.avatar_url)
                        db_ch.banner_url = info.get("banner_url", db_ch.banner_url)
                        db_ch.description = info.get("description", db_ch.description)
                        await session.commit()
        except Exception as e:
            logger.warning("刷新频道详情错误 channel_id={}: {}", ch.channel_id, e)

    logger.info("频道详情刷新完成")


async def daily_backfill_sync() -> None:
    await sync_youtube_videos_full()


async def renew_websub() -> None:
    from app.config import settings

    if (
        not settings.websub_callback_url
        or settings.websub_callback_url == "https://your-domain.com/api/websub/youtube"
    ):
        return

    try:
        await websub_service.subscribe_all_active(settings.websub_callback_url)
        logger.info("WebSub 订阅刷新完成")
    except Exception as e:
        logger.error("WebSub 订阅刷新失败: {}", e)


async def scheduled_scrape_all() -> None:
    try:
        await scrape_and_sync_all()
        logger.info("定时爬取完成")
    except Exception as e:
        logger.error("定时爬取失败: {}", e)
