from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Awaitable

from app.loguru_config import logger


class DanmakuQueue:
    PREFIX = "danmaku:queue:"

    def __init__(self, redis_client: Any):
        self.redis = redis_client
        self._consumers: dict[str, asyncio.Task] = {}
        self._running = False

    async def push(self, video_id: str, messages: list[dict]) -> int:
        if not messages:
            return 0
        for msg in messages:
            await self.redis.rpush(
                f"{self.PREFIX}{video_id}",
                json.dumps(msg, ensure_ascii=False),
            )
        return len(messages)

    async def pop_batch(self, video_id: str, max_count: int = 100) -> list[dict]:
        key = f"{self.PREFIX}{video_id}"
        messages = []
        for _ in range(max_count):
            msg = await self.redis.lpop(key)
            if msg is None:
                break
            try:
                messages.append(json.loads(msg))
            except json.JSONDecodeError:
                logger.warning("Failed to parse danmaku message: {}", msg)
        return messages

    async def get_queue_length(self, video_id: str) -> int:
        length = await self.redis.llen(f"{self.PREFIX}{video_id}")
        return length if length else 0

    async def clear_queue(self, video_id: str) -> None:
        await self.redis.delete(f"{self.PREFIX}{video_id}")

    async def start_consumers(
        self,
        video_ids: list[str],
        handler: Callable[[str, list[dict]], Awaitable[None]],
        interval: float = 0.5,
    ):
        self._running = True

        async def _consume(video_id: str):
            while self._running:
                try:
                    messages = await self.pop_batch(video_id, max_count=100)
                    if messages:
                        await handler(video_id, messages)
                except Exception as e:
                    logger.error("Danmaku consumer error for {}: {}", video_id, e)
                await asyncio.sleep(interval)

        for video_id in video_ids:
            if video_id not in self._consumers:
                self._consumers[video_id] = asyncio.create_task(_consume(video_id))
                logger.info("Started danmaku consumer for {}", video_id)

    async def stop_consumers(self, video_ids: list[str] = None):
        self._running = False
        if video_ids is None:
            video_ids = list(self._consumers.keys())

        for video_id in video_ids:
            task = self._consumers.pop(video_id, None)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                logger.info("Stopped danmaku consumer for {}", video_id)

    async def add_consumer(
        self,
        video_id: str,
        handler: Callable[[str, list[dict]], Awaitable[None]],
        interval: float = 0.5,
    ):
        if video_id in self._consumers:
            return

        async def _consume():
            while self._running:
                try:
                    messages = await self.pop_batch(video_id, max_count=100)
                    if messages:
                        await handler(video_id, messages)
                except Exception as e:
                    logger.error("Danmaku consumer error for {}: {}", video_id, e)
                await asyncio.sleep(interval)

        self._consumers[video_id] = asyncio.create_task(_consume())
        logger.info("Added danmaku consumer for {}", video_id)

    async def remove_consumer(self, video_id: str):
        task = self._consumers.pop(video_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            logger.info("Removed danmaku consumer for {}", video_id)


danmaku_queue = DanmakuQueue(None)


async def init_danmaku_queue(redis_client: Any) -> None:
    danmaku_queue.redis = redis_client
    logger.info("Danmaku queue initialized")
