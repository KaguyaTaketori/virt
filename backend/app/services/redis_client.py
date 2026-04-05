from __future__ import annotations

import redis.asyncio as redis
from redis.asyncio import Redis

from app.config import settings


class RedisClient:
    _instance: Redis = None

    @classmethod
    async def get_client(cls) -> Redis:
        if cls._instance is None:
            cls._instance = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return cls._instance

    @classmethod
    async def close(cls) -> None:
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None
