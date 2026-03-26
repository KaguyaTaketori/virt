from datetime import datetime
from time import timezone

import httpx
import asyncio
import random
from typing import Optional

BILIBILI_LIVE_API = "https://api.live.bilibili.com"
BILIBILI_API      = "https://api.bilibili.com"

# 模拟真实浏览器请求头 — 这是防风控的关键
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


async def get_room_info(
    client: httpx.AsyncClient,
    room_id: str,
) -> Optional[dict]:
    """获取单个直播间状态"""
    # 随机延迟 0.5-1.5s，模拟人工浏览行为
    await asyncio.sleep(random.uniform(0.5, 1.5))
    
    resp = await client.get(
        f"{BILIBILI_LIVE_API}/room/v1/Room/get_info",
        params={"room_id": room_id},
        headers=BASE_HEADERS,
        timeout=10.0,
    )
    resp.raise_for_status()
    data = resp.json()
    
    if data.get("code") != 0:
        return None
    
    return data.get("data")


async def get_rooms_by_uids(
    client: httpx.AsyncClient,
    uids: list[str],
) -> dict:
    """
    批量查询 — 比逐个查询高效得多
    一次最多约 300 个 uid（实测安全值约 100）
    """
    chunk_size = 50  # 保守值，降低触发风控概率
    results = {}
    
    for i in range(0, len(uids), chunk_size):
        chunk = uids[i:i + chunk_size]
        await asyncio.sleep(random.uniform(1.0, 2.0))  # 批次间延迟
        
        resp = await client.get(
            f"{BILIBILI_LIVE_API}/room/v1/Room/rooms_by_uids",
            params={"uids": ",".join(chunk)},
            headers=BASE_HEADERS,
            timeout=15.0,
        )
        
        if resp.status_code == 412:
            # 412 = 触发风控，需要等待更长时间
            print("[Bilibili] Rate limited (412), backing off 60s")
            await asyncio.sleep(60)
            continue
        
        data = resp.json()
        if data.get("code") == 0:
            results.update(data.get("data", {}))
    
    return results


def parse_bilibili_room(data: dict) -> dict:
    """解析 B站直播间数据为统一内部格式"""
    live_status = data.get("live_status", 0)
    
    status_map = {
        0: "offline",
        1: "live",
        2: "upcoming",  # 轮播（视情况处理）
    }
    
    return {
        "video_id": str(data.get("room_id", "")),
        "title": data.get("title"),
        "thumbnail_url": data.get("user_cover") or data.get("keyframe"),
        "status": status_map.get(live_status, "offline"),
        "viewer_count": data.get("online", 0),
        "started_at": (
            datetime.fromtimestamp(data["live_time"], tz=timezone.utc)
            if data.get("live_time") and live_status == 1
            else None
        ),
    }