from __future__ import annotations

import json
from typing import Any, Optional

from app.loguru_config import logger


class PermissionCache:
    PREFIX = "permission:"

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def _get_ttl_seconds(self, token_exp: int) -> int:
        from time import time

        now = int(time())
        ttl = token_exp - now
        return max(ttl, 60)

    async def set_permissions(
        self,
        jti: str,
        roles: set[str],
        permissions: list[dict],
        token_exp: int,
    ) -> None:
        ttl = await self._get_ttl_seconds(token_exp)
        data = {
            "roles": list(roles),
            "permissions": permissions,
        }
        await self.redis.setex(
            f"{self.PREFIX}{jti}",
            ttl,
            json.dumps(data, ensure_ascii=False),
        )

    async def get_permissions(
        self,
        jti: str,
    ) -> Optional[dict]:
        data = await self.redis.get(f"{self.PREFIX}{jti}")
        if data:
            return json.loads(data)
        return None

    async def delete_permissions(self, jti: str) -> None:
        await self.redis.delete(f"{self.PREFIX}{jti}")

    async def delete_all_by_user(self, user_id: int) -> None:
        pattern = f"{self.PREFIX}*"
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


permission_cache = PermissionCache(None)


async def init_permission_cache(redis_client: Any) -> None:
    permission_cache.redis = redis_client
    logger.info("Permission cache initialized")
