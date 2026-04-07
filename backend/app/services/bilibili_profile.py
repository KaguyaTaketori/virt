from __future__ import annotations

import random
import asyncio
from typing import Optional
import httpx

from app.loguru_config import logger
from app.services.bilibili_constants import (
    BILIBILI_API,
    BASE_HEADERS,
    REQ_SLEEP_MIN,
    REQ_SLEEP_MAX,
)


async def get_user_info(client: httpx.AsyncClient, uid: str) -> Optional[dict]:
    await asyncio.sleep(random.uniform(REQ_SLEEP_MIN, REQ_SLEEP_MAX))
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
        data_body = data.get("data", {})
        card = data_body.get("card", {})
        return {
            "name": card.get("name"),
            "avatar_url": card.get("face"),
            "sex": card.get("sex"),
            "sign": card.get("sign"),
            "fans": card.get("fans"),
            "attention": card.get("attention"),
            "archive_count": data_body.get("archive_count"),
            "article_count": data_body.get("article_count"),
            "follower": data_body.get("follower"),
            "like_num": data_body.get("like_num"),
            "level": card.get("level_info", {}).get("current_level"),
            "official_title": card.get("Official", {}).get("title"),
            "official_type": card.get("Official", {}).get("type"),
            "vip_type": card.get("vip", {}).get("type"),
            "vip_status": card.get("vip", {}).get("status"),
        }
    except Exception as e:
        logger.error("get_user_info uid={} error: {}", uid, e)
        return None


async def get_user_info_batch(
    client: httpx.AsyncClient, uids: list[str], max_concurrent: int = 5
) -> dict[str, Optional[dict]]:
    """
    批量并发获取用户信息，带速率限制。
    返回 {uid: info_dict 或 None}
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    results: dict[str, Optional[dict]] = {}

    async def fetch_one(uid: str) -> tuple[str, Optional[dict]]:
        async with semaphore:
            await asyncio.sleep(random.uniform(REQ_SLEEP_MIN, REQ_SLEEP_MAX))
            info = await get_user_info(client, uid)
            return uid, info

    tasks = [fetch_one(uid) for uid in uids]
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    for item in completed:
        if isinstance(item, Exception):
            logger.error("Batch fetch error: {}", item)
            continue
        uid, info = item
        results[uid] = info

    return results
