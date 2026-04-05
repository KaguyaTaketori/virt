from __future__ import annotations

from typing import Any

from app.loguru_config import logger


class RoomCounter:
    PREFIX_VIEWERS = "room:viewers:"
    PREFIX_DANMAKU = "room:danmaku:"

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def add_viewer(self, video_id: str) -> int:
        return await self.redis.incr(f"{self.PREFIX_VIEWERS}{video_id}")

    async def remove_viewer(self, video_id: str) -> int:
        key = f"{self.PREFIX_VIEWERS}{video_id}"
        new_val = await self.redis.decr(key)
        if new_val < 0:
            await self.redis.set(key, 0)
            return 0
        return new_val

    async def get_viewers(self, video_id: str) -> int:
        val = await self.redis.get(f"{self.PREFIX_VIEWERS}{video_id}")
        return int(val) if val else 0

    async def set_viewers(self, video_id: str, count: int) -> None:
        await self.redis.set(f"{self.PREFIX_VIEWERS}{video_id}", count)

    async def increment_danmaku_count(self, video_id: str) -> int:
        return await self.redis.incr(f"{self.PREFIX_DANMAKU}{video_id}")

    async def get_danmaku_count(self, video_id: str) -> int:
        val = await self.redis.get(f"{self.PREFIX_DANMAKU}{video_id}")
        return int(val) if val else 0

    async def set_danmaku_count(self, video_id: str, count: int) -> None:
        await self.redis.set(f"{self.PREFIX_DANMAKU}{video_id}", count)

    async def reset_counts(self, video_id: str) -> None:
        await self.redis.delete(
            f"{self.PREFIX_VIEWERS}{video_id}",
            f"{self.PREFIX_DANMAKU}{video_id}",
        )


room_counter = RoomCounter(None)


async def init_room_counter(redis_client: Any) -> None:
    room_counter.redis = redis_client
    logger.info("Room counter initialized")
