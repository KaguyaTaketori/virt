from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, List, Tuple

from app.loguru_config import logger
from app.services.connection_manager import manager
from app.constants import DANMAKU_MAX_SEEN_IDS, DANMAKU_TRUNCATE_BATCH

try:
    from yt_chat_downloader import YouTubeChatDownloader
    _YT_DOWNLOADER_AVAILABLE = True
except ImportError:
    _YT_DOWNLOADER_AVAILABLE = False

@dataclass
class PollContext:
    api_key: str
    version: str
    continuation: str
    is_live: bool
    downloader: YouTubeChatDownloader = field(default_factory=YouTubeChatDownloader)

class VideoSeenState:
    def __init__(self):
        self.id_set: Set[str] = set()
        self.id_queue: deque[str] = deque()

    def is_new(self, mid: str) -> bool:
        if mid in self.id_set:
            return False
        self.id_set.add(mid)
        self.id_queue.append(mid)
        if len(self.id_queue) > DANMAKU_MAX_SEEN_IDS:
            oldest = self.id_queue.popleft()
            self.id_set.discard(oldest)
        return True

class DanmakuPoller:
    def __init__(self) -> None:
        self._tasks: Dict[str, asyncio.Task] = {}
        self._seen_states: Dict[str, VideoSeenState] = {}

    def start_polling(self, video_id: str) -> None:
        if video_id in self._tasks and not self._tasks[video_id].done():
            return
        
        task = asyncio.create_task(
            self._poll_video_loop(video_id),
            name=f"danmaku_poll_{video_id}",
        )
        task.add_done_callback(lambda t: self._cleanup_task(video_id))
        self._tasks[video_id] = task
        logger.info("Danmaku poll started: {}", video_id)

    def stop_polling(self, video_id: str) -> None:
        task = self._tasks.get(video_id)
        if task and not task.done():
            task.cancel()
            logger.info("Danmaku poll cancellation requested: {}", video_id)

    def _cleanup_task(self, video_id: str) -> None:
        self._tasks.pop(video_id, None)
        self._seen_states.pop(video_id, None)
        logger.debug("Cleaned up resources for video: {}", video_id)

    async def _init_context(self, video_id: str) -> Optional[PollContext]:
        def _sync_init():
            downloader = YouTubeChatDownloader()
            try:
                info = downloader.get_video_info(video_id)
                html = downloader.fetch_html(f"https://www.youtube.com/watch?v={video_id}")
                api_key, version, yid = downloader.extract_innertube_params(html)
                continuation = downloader.find_continuation(yid) if yid else None
                
                if not continuation:
                    return None
                    
                return PollContext(
                    api_key=api_key,
                    version=version,
                    continuation=continuation,
                    is_live=info.get("is_live", False),
                    downloader=downloader
                )
            except Exception as e:
                logger.error("Sync init failed for {}: {}", video_id, e)
                return None

        return await asyncio.to_thread(_sync_init)

    async def _fetch_messages_sync(self, ctx: PollContext) -> Tuple[List[dict], Optional[str]]:
        def _sync():
            chat_data = ctx.downloader.get_live_chat_data(
                ctx.api_key, ctx.version, ctx.continuation, is_live=ctx.is_live
            )
            messages, _ = ctx.downloader.parse_live_chat_messages(chat_data)
            next_cont = ctx.downloader.extract_next_continuation(chat_data)
            return messages, next_cont

        return await asyncio.to_thread(_sync)

    async def _poll_video_loop(self, video_id: str) -> None:
        ctx = await self._init_context(video_id)
        if not ctx:
            logger.warning("Could not initialize context for {}, Task ending.", video_id)
            return

        state = self._seen_states.setdefault(video_id, VideoSeenState())

        while True:
            if not manager.active_connections.get(video_id):
                logger.info("No active subscribers for {}, stopping poll.", video_id)
                break

            try:
                messages, next_cont = await self._fetch_messages_sync(ctx)
                
                new_msgs = []
                for m in messages:
                    mid = m.get("message_id")
                    if mid and state.is_new(mid):
                        new_msgs.append(m)
                    if len(new_msgs) >= DANMAKU_TRUNCATE_BATCH:
                        break

                if new_msgs:
                    await manager.send_message(video_id, {"type": "danmaku", "data": new_msgs})

                if not next_cont:
                    logger.info("No more continuation for {}, ending.", video_id)
                    break
                ctx.continuation = next_cont

                if not ctx.is_live and not new_msgs:
                    break

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Poll error for {}: {}. Retrying in 5s...", video_id, e)
                await asyncio.sleep(5)
                continue

            await asyncio.sleep(1.0 if ctx.is_live else 0.5)

    def get_active_videos(self) -> Set[str]:
        return {vid for vid, t in self._tasks.items() if not t.done()}


poller = DanmakuPoller()