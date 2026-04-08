# backend/app/services/permission_cache.py  (完整替换)
from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from time import time
from typing import Any, Optional

from app.loguru_config import logger


class AbstractPermissionCache(ABC):
    @abstractmethod
    async def set_permissions(self, jti, roles, permissions, token_exp, user_id): ...
    @abstractmethod
    async def get_permissions(self, jti, user_id) -> Optional[dict]: ...
    @abstractmethod
    async def delete_permissions(self, jti, user_id): ...
    @abstractmethod
    async def delete_all_by_user(self, user_id): ...
    @abstractmethod
    async def delete_all(self): ...


class NullPermissionCache(AbstractPermissionCache):
    """安全的空实现，用作默认值。Redis 不可用时系统正常运行（仅无缓存）。"""

    async def set_permissions(self, *args, **kwargs): pass

    async def get_permissions(self, *args, **kwargs) -> None:
        return None  # 明确返回 None，触发 DB 查询

    async def delete_permissions(self, *args, **kwargs): pass
    async def delete_all_by_user(self, *args, **kwargs): pass
    async def delete_all(self, *args, **kwargs): pass


class RedisPermissionCache(AbstractPermissionCache):
    PREFIX = "permission:"

    def __init__(self, redis_client):
        self.redis = redis_client

    def _calc_ttl(self, token_exp: int) -> int:
        return max(token_exp - int(time()), 60)

    def _key(self, jti: str, user_id: int) -> str:
        return f"{self.PREFIX}{user_id}:{jti}"

    async def set_permissions(
        self, jti, roles, permissions, token_exp, user_id
    ) -> None:
        ttl = self._calc_ttl(token_exp)
        data = {"roles": list(roles), "permissions": permissions}
        await self.redis.setex(self._key(jti, user_id), ttl, json.dumps(data))

    async def get_permissions(self, jti: str, user_id: int) -> Optional[dict]:
        try:
            data = await self.redis.get(self._key(jti, user_id))
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning("Permission cache get failed jti={}: {}", jti, e)
            return None  # 降级：返回 None 触发 DB 查询，不抛出异常

    async def delete_permissions(self, jti: str, user_id: int) -> None:
        await self.redis.delete(self._key(jti, user_id))

    async def delete_all_by_user(self, user_id: int) -> None:
        pattern = f"{self.PREFIX}{user_id}:*"
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break

    async def delete_all(self) -> None:
        pattern = f"{self.PREFIX}*"
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break


# ✅ 默认使用 NullPermissionCache，系统启动时安全
_cache_instance: AbstractPermissionCache = NullPermissionCache()
_init_lock = asyncio.Lock()


def get_permission_cache() -> AbstractPermissionCache:
    """依赖注入点，单元测试可替换为 mock"""
    return _cache_instance


async def init_permission_cache(redis_client: Any) -> None:
    """
    初始化 Redis 缓存。失败时保持 NullPermissionCache（降级运行）。
    使用锁确保并发启动时的安全性。
    """
    global _cache_instance
    try:
        await redis_client.ping()  # 健康检查
        async with _init_lock:
            _cache_instance = RedisPermissionCache(redis_client)
        logger.info("Permission cache initialized with Redis")
    except Exception as e:
        logger.warning(
            "Redis permission cache unavailable ({}), degraded mode (no cache)",
            e,
        )
        # _cache_instance 保持 NullPermissionCache，系统继续正常运行


# 兼容旧代码的直接访问
class _CacheProxy:
    """代理模式：旧代码 `permission_cache.get_permissions(...)` 无需改动"""

    def __getattr__(self, name: str):
        return getattr(_cache_instance, name)


permission_cache = _CacheProxy()