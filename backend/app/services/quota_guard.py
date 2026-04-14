# backend/app/services/quota_guard.py  (重构版)
from __future__ import annotations

from datetime import date

from app.loguru_config import logger
from app.config import settings

DAILY_LIMIT    = settings.youtube_quota_daily_limit
DISCOVER_RESERVE = settings.youtube_quota_discover_reserve

COSTS: dict[str, int] = {
    "search.list":       100,
    "videos.list":       1,
    "channels.list":     1,
    "playlistItems.list": 1,
}

_KEY_PREFIX = "quota:"
_redis = None


def _date_key(op: str) -> str:
    return f"{_KEY_PREFIX}{date.today().isoformat()}:{op}"


def _total_key() -> str:
    return f"{_KEY_PREFIX}{date.today().isoformat()}:__total__"


async def init_quota_guard(redis_client) -> None:
    global _redis
    _redis = redis_client
    logger.info("Quota guard initialized with Redis")


async def status() -> dict:
    if _redis is None:
        return {"date": str(date.today()), "used": 0, "limit": DAILY_LIMIT,
                "remaining": DAILY_LIMIT, "ops": {}, "backend": "none"}

    used_raw = await _redis.get(_total_key())
    used = int(used_raw) if used_raw else 0

    keys = await _redis.keys(f"{_KEY_PREFIX}{date.today().isoformat()}:*")
    ops = {}
    for k in keys:
        op_name = k.split(":")[-1]
        if op_name == "__total__":
            continue
        v = await _redis.get(k)
        if v:
            ops[op_name] = int(v)

    return {
        "date":      str(date.today()),
        "used":      used,
        "limit":     DAILY_LIMIT,
        "remaining": max(0, DAILY_LIMIT - used),
        "ops":       ops,
        "backend":   "redis",
    }


async def can_spend(op: str, count: int = 1) -> bool:
    cost = COSTS.get(op, 1) * count

    if _redis is None:
        return True

    used_raw = await _redis.get(_total_key())
    used = int(used_raw) if used_raw else 0
    remaining = DAILY_LIMIT - used

    if remaining < cost:
        logger.warning("拒绝 {}×{}（需要 {}，剩余 {}）", op, count, cost, remaining)
        return False

    if op == "search.list" and (remaining - cost) < DISCOVER_RESERVE:
        logger.warning("search.list 被储备保护拦截（剩余 {}）", remaining)
        return False

    return True


async def spend(op: str, count: int = 1) -> int:
    cost = COSTS.get(op, 1) * count

    if _redis is None:
        return DAILY_LIMIT

    pipe = _redis.pipeline()
    pipe.incrby(_total_key(), cost)
    pipe.expire(_total_key(), 90000)
    pipe.incrby(_date_key(op), count)
    pipe.expire(_date_key(op), 90000)
    results = await pipe.execute()

    total_used = results[0]
    remaining  = max(0, DAILY_LIMIT - total_used)

    logger.info("{} -{} | 已用 {}/{}", op, cost, total_used, DAILY_LIMIT)
    return remaining