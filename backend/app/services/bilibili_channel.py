from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional
from bilibili_api import user

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.loguru_config import logger
from app.models.models import BilibiliDynamic, Video, Platform
from app.services.bilibili_context import ChannelRequestContext
from app.constants import BILIBILI_DEFAULT_PAGE_SIZE, BILIBILI_MAX_VIDEO_PAGES
from app.services.bilibili_api_client import BilibiliApiClient
from app.services.bilibili_parser import BilibiliParser
from app.services.bilibili_repository import BilibiliRepository

MAX_RETRIES = 3
BACKOFF_INIT = 2
BACKOFF_MAX = 60

class BilibiliChannelService:
    def __init__(
        self,
        client: BilibiliApiClient,
        parser: BilibiliParser,
        repo: BilibiliRepository,
    ):
        self._client = client
        self._parser = parser
        self._repo = repo

    async def get_info(
        self, 
        uid: str,
        ctx: ChannelRequestContext,
    ) -> Optional[dict]:
        if not ctx.credential:
            logger.warning("No credential for get_info uid={}", uid)
            return None

        try:
            u = user.User(uid=int(uid), credential=ctx.credential)
            info = await u.get_user_info()
            return self._parser.parse_user_info(info)
        except Exception as e:
            logger.error("Failed to get user info, uid={}: {}", uid, e)
            return None

    async def update_channel(
        self, 
        channel, 
        info: dict,
        db: AsyncSession
    ) -> None:
        """将用户信息应用到 Channel 对象"""
        if not info:
            return
        try:
            changed = False
            if info.get("name") and channel.name != info["name"]:
                channel.name = info["name"]
                changed = True
            if info.get("face") and channel.bilibili_face != info["face"]:
                channel.bilibili_face = info["face"]
                changed = True
            if info.get("sign") and channel.bilibili_sign != info["sign"]:
                channel.bilibili_sign = info["sign"]
                changed = True
            if info.get("fans") is not None:
                channel.bilibili_fans = info["fans"]
                changed = True
            if info.get("archive_count") is not None:
                channel.bilibili_archive_count = info["archive_count"]
                changed = True
            if info.get("attention") is not None:
                channel.bilibili_following = info["attention"]
                changed = True
            if changed and db:
                await db.commit()
        except Exception as e:
            logger.warning("Failed to update channel: {}", e)

    async def get_dynamics(
        self, uid: str, ctx: ChannelRequestContext, offset: str = ""
    ) -> tuple[list, str]:
        if not ctx.credential:
            return [], ""

        raw_result = await self._client.fetch_dynamics(uid, ctx.credential, offset)
        raw_items = raw_result.get("items", [])

        parsed = [p for item in raw_items if (p := self._parser.parse_dynamic(item))]
        await self._repo.upsert_dynamics(ctx.db, ctx.channel_id, parsed, raw_items)

        return parsed, raw_result.get("offset", "")

    async def get_dynamics_from_db(
        self, 
        channel_id: int, 
        db: AsyncSession,
        offset: int = 0, 
        limit: int = BILIBILI_DEFAULT_PAGE_SIZE
    ) -> list:
        if not db:
            return []

        try:
            query = (
                select(BilibiliDynamic)
                .where(BilibiliDynamic.channel_id == channel_id)
                .order_by(BilibiliDynamic.published_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await db.execute(query)
            dynamics = result.scalars().all()

            return [
                {
                    "dynamic_id": d.dynamic_id,
                    "uid": d.uid,
                    "uname": d.uname,
                    "face": d.face,
                    "type": d.type,
                    "timestamp": d.timestamp,
                    "content_nodes": json.loads(d.content_nodes)
                    if d.content_nodes
                    else [],
                    "images": json.loads(d.images) if d.images else [],
                    "repost_content": d.repost_content,
                    "url": d.url,
                    "stat": json.loads(d.stat) if d.stat else {},
                    "topic": d.topic,
                    "is_top": d.is_top,
                }
                for d in dynamics
            ]
        except Exception as e:
            logger.error("Failed to get dynamics from db: {}", e)
            return []

    async def get_videos(
        self, 
        uid: str, 
        ctx: ChannelRequestContext,
        page: int = 1, 
        page_size: int = BILIBILI_DEFAULT_PAGE_SIZE,
    ) -> list:
        if not ctx.credential:
            logger.warning("No credential available for get_videos, uid={}", uid)
            return []

        backoff = BACKOFF_INIT
        for attempt in range(MAX_RETRIES):
            try:
                u = user.User(uid=int(uid), credential=ctx.credential)
                videos_data = await u.get_videos(pn=page, ps=page_size)

                vlist = (videos_data.get("list") or {}).get("vlist") or []

                result = []
                for v in vlist:
                    video_data = self._parser.parse_video(v)
                    result.append(video_data)
                    await self._save_video(ctx, v)

                return result
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
                    logger.error("Failed to get videos, uid={}: {}", uid, e)
                    return []

        logger.warning("uid={} 获取视频重试耗尽", uid)
        return []

    async def get_all_videos(
        self, 
        uid: str, 
        ctx: ChannelRequestContext,
        page_size: int = BILIBILI_DEFAULT_PAGE_SIZE,
    ) -> list:
        if not ctx.credential:
            logger.warning("No credential available for get_all_videos, uid={}", uid)
            return []

        all_videos = []
        page = 1
        max_pages = BILIBILI_MAX_VIDEO_PAGES

        for page in range(1, max_pages + 1):
            videos = await self.get_videos(uid, ctx, page=page, page_size=page_size)
            if not videos:
                break
            all_videos.extend(videos)
            logger.debug("uid={} 第 {} 页获取 {} 个视频", uid, page, len(videos))
            if len(videos) < page_size:
                break

        logger.info("uid={} 共获取 {} 个视频", uid, len(all_videos))
        return all_videos

    async def get_videos_from_db(
        self, 
        channel_id: int, 
        db: AsyncSession,
        page: int = 1, 
        page_size: int = BILIBILI_DEFAULT_PAGE_SIZE
    ) -> list:
        if not db:
            return []

        try:
            query = (
                select(Video)
                .where(
                    Video.channel_id == channel_id,
                    Video.platform == Platform.BILIBILI,
                )
                .order_by(Video.published_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            result = await db.execute(query)
            videos = result.scalars().all()

            return [
                {
                    "bvid": v.video_id,
                    "title": v.title,
                    "pic": v.thumbnail_url,
                    "aid": 0,
                    "duration": v.duration,
                    "pubdate": int(v.published_at.timestamp()) if v.published_at else 0,
                    "play": v.view_count,
                    "like": v.like_count or 0,
                    "reply": 0,
                }
                for v in videos
            ]
        except Exception as e:
            logger.error("Failed to get videos from db: {}", e)
            return []


bilibili_channel_service = BilibiliChannelService(
    client=BilibiliApiClient(),
    parser=BilibiliParser(),
    repo=BilibiliRepository(),
)
