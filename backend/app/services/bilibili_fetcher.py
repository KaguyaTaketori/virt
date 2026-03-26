# backend/app/services/bilibili_fetcher.py
from datetime import datetime, timezone   # ← 修复点
import httpx
import asyncio
import random
from typing import Optional

BILIBILI_LIVE_API = "https://api.live.bilibili.com"
BILIBILI_API      = "https://api.bilibili.com"

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://live.bilibili.com/",
    "Origin": "https://live.bilibili.com",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


async def get_room_info(client: httpx.AsyncClient, room_id: str) -> Optional[dict]:
    await asyncio.sleep(random.uniform(0.5, 1.5))
    resp = await client.get(
        f"{BILIBILI_LIVE_API}/room/v1/Room/get_info",
        params={"room_id": room_id},
        headers=BASE_HEADERS,
        timeout=10.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("data") if data.get("code") == 0 else None


async def get_rooms_by_uids(client: httpx.AsyncClient, uids: list[str]) -> dict:
    chunk_size = 50
    results = {}
    for i in range(0, len(uids), chunk_size):
        chunk = uids[i:i + chunk_size]
        await asyncio.sleep(random.uniform(1.0, 2.0))
        resp = await client.get(
            f"{BILIBILI_LIVE_API}/room/v1/Room/rooms_by_uids",
            params={"uids": ",".join(chunk)},
            headers=BASE_HEADERS,
            timeout=15.0,
        )
        if resp.status_code == 412:
            print("[Bilibili] Rate limited (412), backing off 60s")
            await asyncio.sleep(60)
            continue
        data = resp.json()
        if data.get("code") == 0:
            results.update(data.get("data", {}))
    return results


def parse_bilibili_room(data: dict) -> dict:
    live_status = data.get("live_status", 0)
    status_map = {0: "offline", 1: "live", 2: "upcoming"}

    started_at = None
    live_time = data.get("live_time")
    if live_time and live_status == 1:
        try:
            # B站返回的是 Unix 整数时间戳
            started_at = datetime.fromtimestamp(int(live_time), tz=timezone.utc)
        except (ValueError, OSError, TypeError):
            started_at = None

    return {
        "video_id": str(data.get("room_id", "")),
        "title": data.get("title"),
        "thumbnail_url": data.get("user_cover") or data.get("keyframe"),
        "status": status_map.get(live_status, "offline"),
        "viewer_count": data.get("online", 0),
        "started_at": started_at,
    }