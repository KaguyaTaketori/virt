from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import HTTPException, status

from app.loguru_config import logger
from app.config import settings

DAILY_LIMIT = settings.youtube_quota_daily_limit
DISCOVER_RESERVE = settings.youtube_quota_discover_reserve

QUOTA_COSTS = {
    "search.list": 100,
    "videos.list": 1,
    "channels.list": 1,
    "playlistItems.list": 1,
}


class PermissionDep:
    """
    权限缓存依赖。
    整合 Redis 权限缓存，提供统一的权限查询接口。
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client

    async def get_permissions(self, jti: str, user_id: int) -> Optional[dict]:
        if self._redis is None:
            return None
        try:
            import json

            data = await self._redis.get(f"permission:{user_id}:{jti}")
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning("Permission cache get failed jti={}: {}", jti, e)
            return None

    async def set_permissions(
        self, jti: str, roles: list, permissions: list, token_exp: int, user_id: int
    ) -> None:
        if self._redis is None:
            return
        import json
        from time import time

        ttl = max(token_exp - int(time()), 60)
        data = {"roles": list(roles), "permissions": permissions}
        await self._redis.setex(f"permission:{user_id}:{jti}", ttl, json.dumps(data))

    async def delete_permissions(self, jti: str, user_id: int) -> None:
        if self._redis:
            await self._redis.delete(f"permission:{user_id}:{jti}")

    async def delete_all_by_user(self, user_id: int) -> None:
        if self._redis:
            pattern = f"permission:{user_id}:*"
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self._redis.delete(*keys)
                if cursor == 0:
                    break


class QuotaDep:
    """
    配额守卫依赖。
    整合 YouTube API 配额管理，支持每日限额和预留配额。
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._key_prefix = "quota:"

    def _date_key(self, op: str) -> str:
        return f"{self._key_prefix}{date.today().isoformat()}:{op}"

    def _total_key(self) -> str:
        return f"{self._key_prefix}{date.today().isoformat()}:__total__"

    async def can_spend(self, op: str, count: int = 1) -> bool:
        cost = QUOTA_COSTS.get(op, 1) * count

        if self._redis is None:
            return True

        used_raw = await self._redis.get(self._total_key())
        used = int(used_raw) if used_raw else 0
        remaining = DAILY_LIMIT - used

        if remaining < cost:
            logger.warning("拒绝 {}×{}（需要 {}，剩余 {}）", op, count, cost, remaining)
            return False

        if op == "search.list" and (remaining - cost) < DISCOVER_RESERVE:
            logger.warning("search.list 被储备保护拦截（剩余 {}）", remaining)
            return False

        return True

    async def spend(self, op: str, count: int = 1) -> int:
        cost = QUOTA_COSTS.get(op, 1) * count

        if self._redis is None:
            return DAILY_LIMIT

        pipe = self._redis.pipeline()
        pipe.incrby(self._total_key(), cost)
        pipe.expire(self._total_key(), 90000)
        pipe.incrby(self._date_key(op), count)
        pipe.expire(self._date_key(op), 90000)
        results = await pipe.execute()

        total_used = results[0]
        remaining = max(0, DAILY_LIMIT - total_used)

        logger.info("{} -{} | 已用 {}/{}", op, cost, total_used, DAILY_LIMIT)
        return remaining

    async def status(self) -> dict:
        if self._redis is None:
            return {
                "date": str(date.today()),
                "used": 0,
                "limit": DAILY_LIMIT,
                "remaining": DAILY_LIMIT,
                "ops": {},
                "backend": "none",
            }

        used_raw = await self._redis.get(self._total_key())
        used = int(used_raw) if used_raw else 0

        keys = await self._redis.keys(f"{self._key_prefix}{date.today().isoformat()}:*")
        ops = {}
        for k in keys:
            op_name = k.split(":")[-1]
            if op_name == "__total__":
                continue
            v = await self._redis.get(k)
            if v:
                ops[op_name] = int(v)

        return {
            "date": str(date.today()),
            "used": used,
            "limit": DAILY_LIMIT,
            "remaining": max(0, DAILY_LIMIT - used),
            "ops": ops,
            "backend": "redis",
        }


_permission_dep: Optional[PermissionDep] = None
_quota_dep: Optional[QuotaDep] = None


async def init_deps(redis_client) -> None:
    """初始化 Dependencies（需要 Redis）"""
    global _permission_dep, _quota_dep
    _permission_dep = PermissionDep(redis_client)
    _quota_dep = QuotaDep(redis_client)
    logger.info("Dependencies initialized")


def get_permission_dep() -> PermissionDep:
    return _permission_dep or PermissionDep(None)


def get_quota_dep() -> QuotaDep:
    return _quota_dep or QuotaDep(None)


async def require_quota(op: str, count: int = 1) -> bool:
    """FastAPI Dependency: 检查配额是否足够"""
    quota_dep = get_quota_dep()
    if not await quota_dep.can_spend(op, count):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Quota exceeded for {op}",
        )
    return True
