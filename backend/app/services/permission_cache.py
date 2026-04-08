from __future__ import annotations

import json
from time import time
from typing import Any
from abc import ABC, abstractmethod

from app.loguru_config import logger


class AbstractPermissionCache(ABC):
    @abstractmethod
    async def set_permissions(self, jti, roles, permissions, token_exp, user_id): ...
    @abstractmethod
    async def get_permissions(self, jti, user_id): ...
    @abstractmethod
    async def delete_permissions(self, jti, user_id): ...
    @abstractmethod
    async def delete_all_by_user(self, user_id): ...
    @abstractmethod
    async def delete_all(self): ...

class NullPermissionCache(AbstractPermissionCache):
    async def set_permissions(self, *args, **kwargs): pass
    async def get_permissions(self, *args, **kwargs): return None
    async def delete_permissions(self, *args, **kwargs): pass
    async def delete_all_by_user(self, *args, **kwargs): pass
    async def delete_all(self, *args, **kwargs): pass

class RedisPermissionCache:
    PREFIX = "permission:"

    def __init__(self, redis_client):
        self.redis = redis_client

    def _calc_ttl(self, token_exp: int) -> int:
        now = int(time())
        ttl = token_exp - now
        return max(ttl, 60)
    
    def _key(self, jti: str, user_id: int) -> str:
        return f"{self.PREFIX}{user_id}:{jti}"

    async def set_permissions(self, jti: str, roles, permissions, token_exp, user_id: int):
        ttl = self._calc_ttl(token_exp)
        data = {"roles": list(roles), "permissions": permissions}
        await self.redis.setex(self._key(jti, user_id), ttl, json.dumps(data))

    async def get_permissions(self, jti: str, user_id: int):
        try:
            data = await self.redis.get(self._key(jti, user_id))
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning("Permission cache get failed for jti={}: {}", jti, e)
            return None

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


permission_cache = RedisPermissionCache(None)


async def init_permission_cache(redis_client: Any) -> None:
    permission_cache.redis = redis_client
    logger.info("Permission cache initialized")
