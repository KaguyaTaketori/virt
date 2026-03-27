# backend/app/services/bilibili_fetcher.py  ← 完整替换
from datetime import datetime, timezone
import httpx
import asyncio
import random
from typing import Optional

BILIBILI_LIVE_API = "https://api.live.bilibili.com"
BILIBILI_API = "https://api.bilibili.com"

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


async def get_user_info(client: httpx.AsyncClient, uid: str) -> Optional[dict]:
    """
    拉单个主播的账号信息（头像、名字）。
    接口：/x/web-interface/card — 不需要登录，不需要 WBI 签名。
    每次调用加随机延迟，防止被识别为爬虫。
    """
    await asyncio.sleep(random.uniform(0.8, 1.8))
    try:
        resp = await client.get(
            f"{BILIBILI_API}/x/web-interface/card",
            params={"mid": uid, "photo": "true"},
            headers=BASE_HEADERS,
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            return None
        card = data.get("data", {}).get("card", {})
        return {
            "name": card.get("name"),
            "avatar_url": card.get("face"),  # 头像 URL
        }
    except Exception as e:
        print(f"[Bilibili] get_user_info uid={uid} error: {e}")
        return None


async def get_rooms_by_uids(client: httpx.AsyncClient, uids: list[str]) -> dict:
    """
    批量拉直播状态，逐个查询。
    返回 {uid_str: room_data_dict}。
    遇到风控时退避。
    """
    results = {}

    for uid in uids:
        await asyncio.sleep(random.uniform(1.0, 2.0))

        try:
            resp = await client.get(
                f"{BILIBILI_LIVE_API}/room/v1/Room/getRoomInfoOld",
                params={"mid": uid},
                headers=BASE_HEADERS,
                timeout=15.0,
            )
        except httpx.TimeoutException:
            print(f"[Bilibili] getRoomInfoOld timeout for uid={uid}")
            continue

        if resp.status_code == 412:
            print("[Bilibili] Rate limited (412), backing off 60s")
            await asyncio.sleep(60)
            continue

        try:
            data = resp.json()
        except Exception:
            continue

        if data.get("code") == 0:
            room_data = data.get("data", {})
            if room_data:
                results[str(uid)] = {
                    "room_id": room_data.get("roomid"),
                    "title": room_data.get("title"),
                    "user_cover": room_data.get("cover"),
                    "live_status": room_data.get("liveStatus"),
                    "online": room_data.get("online"),
                }

    return results


def parse_bilibili_room(room: dict) -> dict:
    """
    把 rooms_by_uids 返回的单条 room 数据解析成统一内部格式。
    live_status: 0=未开播, 1=直播中, 2=轮播
    """
    live_status = room.get("live_status", 0)
    status_map = {0: "offline", 1: "live", 2: "upcoming"}

    started_at = None
    live_time = room.get("live_time")
    if live_time and live_status == 1:
        try:
            started_at = datetime.fromtimestamp(int(live_time), tz=timezone.utc)
        except (ValueError, OSError, TypeError):
            pass

    return {
        "video_id": str(room.get("room_id", "")),
        "title": room.get("title"),
        "thumbnail_url": room.get("user_cover") or room.get("keyframe"),
        "status": status_map.get(live_status, "offline"),
        "viewer_count": room.get("online", 0),
        "started_at": started_at,
    }
