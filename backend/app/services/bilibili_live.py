from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from typing import Optional, Dict, List
from bilibili_api import user, live, Credential

from app.loguru_config import logger
from app.config import settings
from app.services.bilibili_constants import (
    BATCH_SIZE,
    BATCH_SLEEP_MIN,
    BATCH_SLEEP_MAX,
    REQ_SLEEP_MIN,
    REQ_SLEEP_MAX,
)


def _create_credential() -> Optional[Credential]:
    if not settings.bilibili_sessdata:
        return None
    try:
        return Credential(sessdata=settings.bilibili_sessdata)
    except Exception as e:
        logger.warning("Failed to create Bilibili credential: {}", e)
        return None


async def _fetch_single_room(
    uid: str,
    credential: Optional[Credential],
) -> Optional[Dict]:
    if not credential:
        return None

    backoff = 2
    for attempt in range(3):
        try:
            u = user.User(uid=int(uid), credential=credential)
            info = await u.get_user_info()

            live_room = info.get("live_room")
            if not live_room:
                return None

            room_id = live_room.get("room_id", 0)
            if not room_id:
                return None

            room = live.LiveRoom(room_id=int(room_id), credential=credential)
            room_info = await room.get_room_info()

            if room_info:
                return {
                    "room_id": room_info.get("room_id"),
                    "title": room_info.get("title"),
                    "user_cover": room_info.get("user_cover"),
                    "live_status": room_info.get("live_status"),
                    "online": room_info.get("online"),
                    "live_time": room_info.get("live_time"),
                }
            return None
        except Exception as e:
            error_msg = str(e)
            if "412" in error_msg:
                logger.warning(
                    "触发风控 412 uid={}，退避 {}s (attempt {})",
                    uid,
                    backoff,
                    attempt + 1,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
            else:
                logger.warning(
                    "获取房间信息失败 uid={} attempt={}: {}", uid, attempt + 1, e
                )
                await asyncio.sleep(1)

    return None


async def get_rooms_by_uids(
    uids: List[str],
    credential: Optional[Credential] = None,
    max_concurrent: int = 5,
) -> Dict[str, Dict]:
    if not credential:
        credential = _create_credential()

    semaphore = asyncio.Semaphore(max_concurrent)
    results: Dict[str, Dict] = {}

    async def fetch_with_limit(uid: str) -> tuple[str, Optional[Dict]]:
        async with semaphore:
            await asyncio.sleep(random.uniform(REQ_SLEEP_MIN, REQ_SLEEP_MAX))
            room = await _fetch_single_room(uid, credential)
            return uid, room

    tasks = [fetch_with_limit(uid) for uid in uids]
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    for item in completed:
        if isinstance(item, Exception):
            logger.error("Batch fetch error: {}", item)
            continue
        uid, room = item
        if room:
            results[uid] = room

    logger.info("获取 {} 个房间（共 {} 个 UID）", len(results), len(uids))
    return results


def parse_bilibili_room(room: Dict) -> Dict:
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
