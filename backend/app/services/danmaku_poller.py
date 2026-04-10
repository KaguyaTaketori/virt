from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from app.loguru_config import logger
from app.services.connection_manager import manager
from app.constants import DANMAKU_MAX_SEEN_IDS, DANMAKU_TRUNCATE_BATCH

try:
    from yt_chat_downloader import YouTubeChatDownloader
    _YT_DOWNLOADER_AVAILABLE = True
except ImportError:
    _YT_DOWNLOADER_AVAILABLE = False
    YouTubeChatDownloader = None

@dataclass
class PollContext:
    downloader: any
    api_key: str
    version: str
    continuation: str
    is_live: bool

class DanmakuPoller:
    def __init__(self) -> None:
        self._tasks: Dict[str, asyncio.Task] = {}
        self._seen_ids_queue: deque[str] = deque()
        self._seen_ids_set: set[str] = set()
        self._seen_lock = asyncio.Lock()

    async def _add_seen(self, mid: str) -> bool:
        async with self._seen_lock:
            if mid in self._seen_ids_set:
                return False
            self._seen_ids_set.add(mid)
            self._seen_ids_queue.append(mid)
            if len(self._seen_ids_queue) > DANMAKU_MAX_SEEN_IDS:
                oldest = self._seen_ids_queue.popleft()
                self._seen_ids_set.discard(oldest)
            return True

    def start_polling(self, video_id: str) -> None:
        if video_id in self._tasks and not self._tasks[video_id].done():
            return
        task = asyncio.create_task(
            self._poll_video(video_id),
            name=f"danmaku_poll_{video_id}",
        )
        task.add_done_callback(lambda t: self._on_task_done(video_id, t))
        self._tasks[video_id] = task
        logger.info("danmaku poll started: {}", video_id)

    def stop_polling(self, video_id: str) -> None:
        task = self._tasks.pop(video_id, None)
        if task and not task.done():
            task.cancel()
            logger.info("danmaku poll cancelled: {}", video_id)

    def get_active_videos(self) -> Set[str]:
        return {vid for vid, t in self._tasks.items() if not t.done()}

    def _on_task_done(self, video_id: str, task: asyncio.Task) -> None:
        self._tasks.pop(video_id, None)
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            logger.error("danmaku poll error for {}: {}", video_id, exc)

    async def _poll_video(self, video_id: str) -> None:
        ctx = await self._init_poll_context(video_id)
        if ctx is None:
            return
        if ctx.is_live:
            await self._run_live_loop(video_id, ctx)
        else:
            await self._fetch_and_send(video_id, ctx)

    async def _init_poll_context(self, video_id: str) -> Optional[PollContext]:
        downloader = YouTubeChatDownloader()
        try:
            info = await asyncio.to_thread(downloader.get_video_info, video_id)
            html = await asyncio.to_thread(
                downloader.fetch_html,
                f"https://www.youtube.com/watch?v={video_id}"
            )
            api_key, version, yid = await asyncio.to_thread(
                downloader.extract_innertube_params, html
            )
            continuation = (
                await asyncio.to_thread(downloader.find_continuation, yid)
                if yid else None
            )
            if not continuation:
                return None
            return PollContext(
                downloader=downloader,
                api_key=api_key,
                version=version,
                continuation=continuation,
                is_live=info.get("is_live", False),
            )
        except Exception as e:
            logger.error("poll init failed for {}: {}", video_id, e)
            return None

    async def _run_live_loop(self, video_id: str, ctx: PollContext) -> None:
        while True:
            if not manager.active_connections.get(video_id):
                logger.info("no subscribers for {}, stopping", video_id)
                return
            try:
                next_continuation = await self._fetch_and_send(video_id, ctx)
                if not next_continuation:
                    return
                ctx = PollContext(
                    downloader=ctx.downloader,
                    api_key=ctx.api_key,
                    version=ctx.version,
                    continuation=next_continuation,
                    is_live=True,
                )
            except Exception as e:
                logger.error("poll loop error for {}: {}", video_id, e)
                await asyncio.sleep(5)
            await asyncio.sleep(1.0)

    async def _fetch_and_send(
        self,
        video_id: str,
        ctx: PollContext,
    ) -> Optional[str]:
        try:
            chat_data = await asyncio.to_thread(
                ctx.downloader.get_live_chat_data,
                ctx.api_key, ctx.version, ctx.continuation, is_live=ctx.is_live,
            )
            messages, _ = await asyncio.to_thread(
                ctx.downloader.parse_live_chat_messages, chat_data
            )
            next_cont = await asyncio.to_thread(
                ctx.downloader.extract_next_continuation, chat_data
            )
        except Exception as e:
            logger.error("fetch error for {}: {}", video_id, e)
            return ctx.continuation

        new_msgs: list[dict] = []
        for m in messages:
            mid = m.get("message_id", "")
            if mid and await self._add_seen(mid):
                new_msgs.append(m)
            if len(new_msgs) >= DANMAKU_TRUNCATE_BATCH:
                break

        if new_msgs:
            await manager.send_message(video_id, {"type": "danmaku", "data": new_msgs})
        return next_cont


poller = DanmakuPoller()