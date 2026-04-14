from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional

from app.loguru_config import logger
from app.services.redis_client import RedisClient


class RedisLock:
    """基于 Redis 的分布式锁。"""

    def __init__(
        self,
        key: str,
        timeout: int = 300,
        retry_times: int = 3,
        retry_delay: float = 0.2,
    ):
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.retry_times = retry_times
        self.retry_delay = retry_delay
        self._locked = False

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()

    async def acquire(self) -> bool:
        """尝试获取锁。"""
        redis = await RedisClient.get_client()
        lock_val = str(time.time())

        for attempt in range(self.retry_times):
            ok = await redis.set(self.key, lock_val, nx=True, ex=self.timeout)
            if ok:
                self._locked = True
                return True

            await asyncio.sleep(self.retry_delay)

        return False

    async def release(self) -> bool:
        """释放锁。"""
        if not self._locked:
            return False

        redis = await RedisClient.get_client()
        await redis.delete(self.key)
        self._locked = False
        return True

    @classmethod
    @asynccontextmanager
    async def acquire_lock(
        cls,
        key: str,
        timeout: int = 300,
        retry_times: int = 3,
    ):
        """上下文管理器方式使用锁。"""
        lock = cls(key, timeout=timeout, retry_times=retry_times)
        acquired = await lock.acquire()

        if not acquired:
            logger.warning("获取锁失败: {}", key)
            yield False
            return

        try:
            yield True
        finally:
            await lock.release()


@asynccontextmanager
async def distributed_lock(
    key: str,
    timeout: int = 300,
):
    """简化的分布式锁上下文管理器。"""
    async with RedisLock.acquire_lock(key, timeout=timeout) as acquired:
        if acquired:
            yield True
        else:
            yield False
