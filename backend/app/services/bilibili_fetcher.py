# backend/app/services/bilibili_fetcher.py
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from typing import Optional

import httpx

BILIBILI_LIVE_API = "https://api.live.bilibili.com"
BILIBILI_API = "https://api.bilibili.com"

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://live.bilibili.com/",
    "Origin": "https://live.bilibili.com",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept": "application/json, text/plain, */*",
}

# 退避参数
_BACKOFF_INIT    = 60     # 首次 412 退避 60 秒
_BACKOFF_MAX     = 600    # 最长退避 10 分钟
_BACKOFF_FACTOR  = 2      # 每次翻倍
_MAX_RETRIES     = 3      # 单个 uid 最多重试次数


async def get_user_info(client: httpx.AsyncClient, uid: str) -> Optional[dict]:
    """
    拉单个主播账号信息（头像、名字）。
    接口：/x/web-interface/card — 不需要登录。
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
            "name":       card.get("name"),
            "avatar_url": card.get("face"),
        }
    except Exception as e:
        print(f"[Bilibili] get_user_info uid={uid} error: {e}")
        return None


async def get_rooms_by_uids(
    client: httpx.AsyncClient,
    uids: list[str],
) -> dict:
    """
    批量拉直播状态，单线程串行 + 指数退避防风控。
    返回 {uid_str: room_data_dict}。

    退避状态在本次调用内共享：一旦触发 412，
    之后每个 uid 都等待当前退避时长，直到退避重置。
    """
    results: dict[str, dict] = {}
    current_backoff = _BACKOFF_INIT

    for uid in uids:
        # 正常请求间隔（随机化防指纹）
        await asyncio.sleep(random.uniform(1.2, 2.8))

        success = False
        for attempt in range(_MAX_RETRIES):
            try:
                resp = await client.get(
                    f"{BILIBILI_LIVE_API}/room/v1/Room/getRoomInfoOld",
                    params={"mid": uid},
                    headers=BASE_HEADERS,
                    timeout=15.0,
                )
            except httpx.TimeoutException:
                print(f"[Bilibili] 超时 uid={uid} attempt={attempt + 1}/{_MAX_RETRIES}")
                await asyncio.sleep(5)
                continue
            except httpx.RequestError as e:
                print(f"[Bilibili] 网络错误 uid={uid}: {e}")
                break

            # 风控触发
            if resp.status_code == 412:
                print(
                    f"[Bilibili] 风控 412 uid={uid}，退避 {current_backoff}s "
                    f"（attempt {attempt + 1}/{_MAX_RETRIES}）"
                )
                await asyncio.sleep(current_backoff)
                current_backoff = min(current_backoff * _BACKOFF_FACTOR, _BACKOFF_MAX)
                continue

            # 其他非 200
            if resp.status_code != 200:
                print(f"[Bilibili] 非预期状态 {resp.status_code} uid={uid}")
                break

            # 解析响应
            try:
                data = resp.json()
            except Exception:
                print(f"[Bilibili] JSON 解析失败 uid={uid}")
                break

            if data.get("code") == 0:
                room_data = data.get("data", {})
                if room_data:
                    results[str(uid)] = {
                        "room_id":    room_data.get("roomid"),
                        "title":      room_data.get("title"),
                        "user_cover": room_data.get("cover"),
                        "live_status": room_data.get("liveStatus"),
                        "online":     room_data.get("online"),
                        "live_time":  room_data.get("live_time"),
                    }

            # 成功：重置退避计时器
            current_backoff = _BACKOFF_INIT
            success = True
            break

        if not success:
            print(f"[Bilibili] uid={uid} 最终失败，已跳过")

    return results


def parse_bilibili_room(room: dict) -> dict:
    """
    把 get_rooms_by_uids 返回的单条 room 解析成统一内部格式。
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
        "video_id":     str(room.get("room_id", "")),
        "title":        room.get("title"),
        "thumbnail_url": room.get("user_cover") or room.get("keyframe"),
        "status":       status_map.get(live_status, "offline"),
        "viewer_count": room.get("online", 0),
        "started_at":   started_at,
    }