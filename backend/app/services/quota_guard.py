from __future__ import annotations
import asyncio
import json
from datetime import date
from pathlib import Path
from app.loguru_config import logger

QUOTA_FILE = Path("./quota_state.json")
DAILY_LIMIT = 9_500
DISCOVER_RESERVE = 2_000
COSTS: dict[str, int] = {
    "search.list": 100,
    "videos.list": 1,
    "channels.list": 1,
    "playlistItems.list": 1,
}

_lock = asyncio.Lock()
_state: dict = {}


def _fresh_state() -> dict:
    return {"date": str(date.today()), "used": 0, "ops": {}}


def _load_from_disk() -> dict:
    if QUOTA_FILE.exists():
        try:
            data = json.loads(QUOTA_FILE.read_text())
            if data.get("date") == str(date.today()):
                return data
        except Exception:
            pass
    return _fresh_state()


async def _init():
    global _state
    if not _state or _state.get("date") != str(date.today()):
        _state = await asyncio.to_thread(_load_from_disk)


async def _persist():
    data = dict(_state)
    await asyncio.to_thread(
        lambda: QUOTA_FILE.write_text(json.dumps(data, indent=2))
    )


async def status() -> dict:
    async with _lock:
        await _init()
        used = _state["used"]
        return {
            "date": _state["date"],
            "used": used,
            "limit": DAILY_LIMIT,
            "remaining": max(0, DAILY_LIMIT - used),
            "ops": dict(_state.get("ops", {})),
        }


async def can_spend(op: str, count: int = 1) -> bool:
    cost = COSTS.get(op, 1) * count
    async with _lock:
        await _init()
        remaining = DAILY_LIMIT - _state["used"]
        if remaining < cost:
            logger.warning("拒绝 {}×{}（需要 {}，剩余 {}）", op, count, cost, remaining)
            return False
        if op == "search.list" and (remaining - cost) < DISCOVER_RESERVE:
            logger.warning("search.list 被储备保护拦截（剩余 {}）", remaining)
            return False
        return True


async def spend(op: str, count: int = 1) -> int:
    cost = COSTS.get(op, 1) * count
    async with _lock:
        await _init()
        _state["used"] += cost
        _state["ops"][op] = _state["ops"].get(op, 0) + count
        remaining = max(0, DAILY_LIMIT - _state["used"])
        logger.info("{} -{} | 已用 {}/{}", op, cost, _state["used"], DAILY_LIMIT)
    await _persist()
    return remaining