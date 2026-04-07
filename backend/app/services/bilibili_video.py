from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Optional, List, Dict
from bilibili_api import user, Credential

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Video, Platform
from app.loguru_config import logger
from app.config import settings

MAX_RETRIES = 3
BACKOFF_INIT = 2
BACKOFF_MAX = 60


def _create_credential() -> Optional[Credential]:
    if not settings.bilibili_sessdata:
        return None
    try:
        return Credential(sessdata=settings.bilibili_sessdata)
    except Exception as e:
        logger.warning("Failed to create Bilibili credential: {}", e)
        return None


async def get_user_videos(
    credential: Optional[Credential],
    uid: str,
    pn: int = 1,
    ps: int = 30,
) -> Optional[List[Dict]]:
    if not credential:
        logger.warning("No credential available for get_user_videos, uid={}", uid)
        return None

    backoff = BACKOFF_INIT
    for attempt in range(MAX_RETRIES):
        try:
            u = user.User(uid=int(uid), credential=credential)
            videos_data = await u.get_videos(pn=pn, ps=ps)

            vlist = (videos_data.get("list") or {}).get("vlist") or []
            return vlist
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
                backoff = min(backoff * 2, BACKOFF_MAX)
            else:
                logger.error("Failed to get user videos, uid={}: {}", uid, e)
                return None

    logger.warning("uid={} 重试耗尽，跳过", uid)
    return None


async def sync_bilibili_channel_videos(
    db: AsyncSession, channel_id: int, channel_id_str: str
) -> int:
    credential = _create_credential()
    if not credential:
        logger.warning(
            "No credential available for sync_bilibili_channel_videos, channel_id={}",
            channel_id,
        )
        return 0

    total_synced = 0
    page = 1
    page_size = 30

    while True:
        vlist = await get_user_videos(credential, channel_id_str, page, page_size)
        if not vlist:
            break

        for v in vlist:
            bvid = v.get("bvid", "")
            if not bvid:
                continue

            result = await db.execute(
                select(Video).where(
                    Video.channel_id == channel_id, Video.video_id == bvid
                )
            )
            existing = result.scalar_one_or_none()

            published = None
            if v.get("created"):
                try:
                    published = datetime.fromtimestamp(v.get("created"))
                except Exception:
                    pass

            if existing:
                existing.title = v.get("title")
                existing.thumbnail_url = v.get("pic", "")
                existing.view_count = v.get("play", 0)
                existing.duration = v.get("length", "")
                existing.published_at = published
            else:
                video = Video(
                    channel_id=channel_id,
                    platform=Platform.BILIBILI,
                    video_id=bvid,
                    title=v.get("title", ""),
                    thumbnail_url=v.get("pic", ""),
                    duration=v.get("length", ""),
                    view_count=v.get("play", 0),
                    published_at=published,
                    status="archive",
                )
                db.add(video)
            total_synced += 1

        await db.commit()

        if len(vlist) < page_size:
            break
        page += 1
        await asyncio.sleep(2)

    return total_synced
