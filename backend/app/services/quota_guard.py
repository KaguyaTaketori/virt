from __future__ import annotations

import json
import threading
from datetime import date
from pathlib import Path
from typing import Literal

QUOTA_FILE = Path("./quota_state.json")
DAILY_LIMIT = 9_500
DISCOVER_RESERVE = 2_000

COSTS: dict[str, int] = {
    "search.list":        100,
    "videos.list":        1,
    "channels.list":      1,
    "playlistItems.list": 1,
}

_lock = threading.Lock()


# ── 内部 I/O ──────────────────────────────────────────────────────────────────

def _load() -> dict:
    """读取配额状态，如果不是今天的数据则重置。"""
    if QUOTA_FILE.exists():
        try:
            data = json.loads(QUOTA_FILE.read_text())
            if data.get("date") == str(date.today()):
                return data
        except (json.JSONDecodeError, KeyError):
            pass
    return {"date": str(date.today()), "used": 0, "ops": {}}


def _save(data: dict) -> None:
    QUOTA_FILE.write_text(json.dumps(data, indent=2))


# ── 公开 API ──────────────────────────────────────────────────────────────────

def status() -> dict:
    """返回当日配额状态，供 /api/admin/quota 端点使用。"""
    with _lock:
        data = _load()
        used = data["used"]
        return {
            "date":      data["date"],
            "used":      used,
            "limit":     DAILY_LIMIT,
            "remaining": max(0, DAILY_LIMIT - used),
            "ops":       data.get("ops", {}),
        }


def can_spend(op: str, count: int = 1) -> bool:
    """
    检查能否执行 count 次 op 操作。
    discover 类操作额外受 DISCOVER_RESERVE 限制。
    """
    cost = COSTS.get(op, 1) * count
    with _lock:
        data = _load()
        remaining = DAILY_LIMIT - data["used"]
        if remaining < cost:
            print(f"[QuotaGuard] 拒绝 {op}×{count}（需要 {cost}，剩余 {remaining}）")
            return False
        if op == "search.list" and remaining - cost < DAILY_LIMIT - DISCOVER_RESERVE - data["used"]:
            pass
        return True


def spend(op: str, count: int = 1) -> int:
    """
    扣减配额并持久化。返回扣减后剩余配额。
    即使 can_spend 已检查，这里仍做二次保护。
    """
    cost = COSTS.get(op, 1) * count
    with _lock:
        data = _load()
        data["used"] += cost
        data["ops"][op] = data["ops"].get(op, 0) + count
        _save(data)
        remaining = max(0, DAILY_LIMIT - data["used"])
        print(f"[QuotaGuard] {op}×{count} -{cost} | 今日已用 {data['used']}/{DAILY_LIMIT}（剩余 {remaining}）")
        return remaining


def remaining() -> int:
    """快速查剩余配额（不加锁，用于日志）。"""
    data = _load()
    return max(0, DAILY_LIMIT - data["used"])