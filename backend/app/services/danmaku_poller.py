from __future__ import annotations

import asyncio
from collections import deque
from typing import Dict, List, Optional, Set

from app.loguru_config import logger
from app.services.connection_manager import manager
from app.services.constants import DANMAKU_MAX_SEEN_IDS, DANMAKU_TRUNCATE_BATCH

try:
    from yt_chat_downloader import YouTubeChatDownloader
    _YT_DOWNLOADER_AVAILABLE = True
except ImportError:
    _YT_DOWNLOADER_AVAILABLE = False
    YouTubeChatDownloader = None

seen_ids_queue: deque[str] = deque()
seen_ids_set: set[str] = set()

def add_seen(mid: str) -> bool:
    if mid in seen_ids_set:
        return False
    
    seen_ids_set.add(mid)
    seen_ids_queue.append(mid)
    
    if len(seen_ids_queue) > DANMAKU_MAX_SEEN_IDS:
        oldest = seen_ids_queue.popleft()
        seen_ids_set.discard(oldest)
    return True


class DanmakuPoller:

    def __init__(self) -> None:
        self._tasks: Dict[str, asyncio.Task] = {}

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
        if not _YT_DOWNLOADER_AVAILABLE:
            logger.warning("yt_chat_downloader not available, skipping poll for {}", video_id)
            return

        downloader = YouTubeChatDownloader()
        continuation: Optional[str] = None
        api_key: Optional[str] = None
        version: Optional[str] = None
        is_live = False

        try:
            info = await asyncio.to_thread(downloader.get_video_info, video_id)
            is_live = info.get("is_live", False)

            html = await asyncio.to_thread(
                downloader.fetch_html,
                f"https://www.youtube.com/watch?v={video_id}",
            )
            api_key, version, yid = await asyncio.to_thread(
                downloader.extract_innertube_params, html
            )
            if yid:
                continuation = await asyncio.to_thread(downloader.find_continuation, yid)
            logger.info("poll init ok: {} live={} cont={}", video_id, is_live, bool(continuation))
        except Exception as e:
            logger.error("poll init failed for {}: {}", video_id, e)
            return

        if not continuation:
            return

        if not is_live:
            await self._fetch_and_send(downloader, video_id, api_key, version,
                                       continuation, is_live)
            return

        while True:
            if not manager.active_connections.get(video_id):
                logger.info("no subscribers for {}, stopping poll", video_id)
                return

            try:
                continuation = await self._fetch_and_send(
                    downloader, video_id, api_key, version,
                    continuation, is_live
                )
                if not continuation:
                    logger.info("no more continuation for {}", video_id)
                    return
            except Exception as e:
                logger.error("poll loop error for {}: {}", video_id, e)
                await asyncio.sleep(5)
                continue

            await asyncio.sleep(1.0)

    async def _fetch_and_send(
        self,
        downloader,
        video_id: str,
        api_key: str,
        version: str,
        continuation: str,
        is_live: bool,
    ) -> Optional[str]:
        try:
            chat_data = await asyncio.to_thread(
                downloader.get_live_chat_data,
                api_key, version, continuation, is_live=is_live,
            )
            messages, _ = await asyncio.to_thread(
                downloader.parse_live_chat_messages, chat_data
            )
            next_cont = await asyncio.to_thread(
                downloader.extract_next_continuation, chat_data
            )
        except Exception as e:
            logger.error("fetch error for {}: {}", video_id, e)
            return continuation

        new_msgs: List[dict] = []
        for m in messages:
            mid = m.get("message_id", "")
            if mid and add_seen(mid):
                new_msgs.append(m)

        if len(new_msgs) > DANMAKU_TRUNCATE_BATCH:
            new_msgs = new_msgs[-DANMAKU_TRUNCATE_BATCH:]

        if new_msgs:
            await manager.send_message(video_id, {"type": "danmaku", "data": new_msgs})

        return next_cont


poller = DanmakuPoller()