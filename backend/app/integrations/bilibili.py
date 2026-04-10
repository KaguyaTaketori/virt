from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from typing import Optional

from bilibili_api import user, live, Credential

from app.config import settings
from app.integrations.base import (
    BaseLivePlatform,
    ChannelInfo,
    LiveStatus,
    LiveStatusEnum,
    PaginatedVideos,
    VideoItem,
)
from app.loguru_config import logger
from app.models.models import Platform

BILIBILI_API_BASE = "https://api.bilibili.com"
BILIBILI_LIVE_API_BASE = "https://api.live.bilibili.com"

REQ_SLEEP_MIN = 1.0
REQ_SLEEP_MAX = 2.2
MAX_CONCURRENT = 5


def _create_credential() -> Optional[Credential]:
    if not settings.bilibili_sessdata:
        return None
    try:
        return Credential(sessdata=settings.bilibili_sessdata)
    except Exception as e:
        logger.warning("Failed to create Bilibili credential: %s", e)
        return None


class BilibiliPlatform(BaseLivePlatform):
    PLATFORM = Platform.BILIBILI

    async def get_channel_info(self, channel_id: str) -> Optional[ChannelInfo]:
        credential = _create_credential()
        if not credential:
            return None

        try:
            u = user.User(uid=int(channel_id), credential=credential)
            user_info = await u.get_user_info()

            info = user_info.get("info", {})
            detail = user_info.get("detail", {})
            stats = user_info.get("stat", {})

            return ChannelInfo(
                platform=Platform.BILIBILI,
                channel_id=channel_id,
                name=info.get("uname", ""),
                avatar_url=info.get("face"),
                description=detail.get("sign"),
                bilibili_sign=detail.get("sign"),
                bilibili_fans=stats.get("follower"),
                bilibili_archive_count=info.get("archive", {}).get("count"),
                bilibili_face=info.get("face"),
            )
        except Exception as e:
            logger.warning("Bilibili get_channel_info error: %s", e)

        return None

    async def resolve_channel_id(self, input_str: str) -> Optional[str]:
        if not input_str:
            return None

        input_str = input_str.strip()

        if input_str.isdigit():
            return input_str

        if input_str.startswith("https://space.bilibili.com/"):
            match = input_str.split("/")[-1].split("?")[0]
            if match.isdigit():
                return match

        if input_str.startswith("UC") or input_str.startswith("U"):
            return None

        return None

    async def get_live_status(self, channel_id: str) -> Optional[LiveStatus]:
        credential = _create_credential()
        if not credential:
            return None

        backoff = 2
        for attempt in range(3):
            try:
                u = user.User(uid=int(channel_id), credential=credential)
                user_info = await u.get_user_info()

                live_room = user_info.get("live_room")
                if not live_room:
                    return LiveStatus(
                        video_id=None,
                        title=None,
                        thumbnail_url=None,
                        status=LiveStatusEnum.OFFLINE,
                        viewer_count=0,
                    )

                room_id = live_room.get("room_id", 0)
                if not room_id:
                    return LiveStatus(
                        video_id=None,
                        title=None,
                        thumbnail_url=None,
                        status=LiveStatusEnum.OFFLINE,
                        viewer_count=0,
                    )

                room = live.LiveRoom(room_id=int(room_id), credential=credential)
                room_info = await room.get_room_info()

                if not room_info:
                    return LiveStatus(
                        video_id=None,
                        title=None,
                        thumbnail_url=None,
                        status=LiveStatusEnum.OFFLINE,
                        viewer_count=0,
                    )

                live_status = room_info.get("live_status", 0)
                if live_status == 1:
                    started_at = None
                    live_time = room_info.get("live_time")
                    if live_time:
                        try:
                            started_at = datetime.fromtimestamp(
                                int(live_time), tz=timezone.utc
                            )
                        except (ValueError, OSError, TypeError):
                            pass

                    return LiveStatus(
                        video_id=str(room_info.get("room_id", "")),
                        title=room_info.get("title"),
                        thumbnail_url=room_info.get("user_cover")
                        or room_info.get("keyframe"),
                        status=LiveStatusEnum.LIVE,
                        viewer_count=room_info.get("online", 0),
                        started_at=started_at,
                    )
                elif live_status == 2:
                    scheduled_at = None
                    live_time = room_info.get("live_time")
                    if live_time:
                        try:
                            scheduled_at = datetime.fromtimestamp(
                                int(live_time), tz=timezone.utc
                            )
                        except (ValueError, OSError, TypeError):
                            pass

                    return LiveStatus(
                        video_id=str(room_info.get("room_id", "")),
                        title=room_info.get("title"),
                        thumbnail_url=room_info.get("user_cover"),
                        status=LiveStatusEnum.UPCOMING,
                        viewer_count=0,
                        scheduled_at=scheduled_at,
                    )

                return LiveStatus(
                    video_id=None,
                    title=None,
                    thumbnail_url=None,
                    status=LiveStatusEnum.OFFLINE,
                    viewer_count=0,
                )

            except Exception as e:
                error_msg = str(e)
                if "412" in error_msg:
                    logger.warning(
                        "Bilibili rate limit 412 for %s, backoff %ds (attempt %d)",
                        channel_id,
                        backoff,
                        attempt + 1,
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 60)
                else:
                    logger.warning(
                        "Bilibili get_live_status error uid=%s attempt=%d: %s",
                        channel_id,
                        attempt + 1,
                        e,
                    )
                    await asyncio.sleep(1)

        return None

    async def batch_get_live_status(
        self, channel_ids: list[str], max_concurrent: int = MAX_CONCURRENT
    ) -> dict[str, Optional[LiveStatus]]:
        if not channel_ids:
            return {}

        credential = _create_credential()

        semaphore = asyncio.Semaphore(max_concurrent)
        results: dict[str, Optional[LiveStatus]] = {}

        async def fetch_with_limit(uid: str) -> tuple[str, Optional[LiveStatus]]:
            async with semaphore:
                await asyncio.sleep(random.uniform(REQ_SLEEP_MIN, REQ_SLEEP_MAX))
                status = await self.get_live_status(uid)
                return uid, status

        tasks = [fetch_with_limit(uid) for uid in channel_ids]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for item in completed:
            if isinstance(item, Exception):
                logger.error("Bilibili batch fetch error: %s", item)
                continue
            uid, status = item
            results[uid] = status

        logger.debug(
            "Bilibili batch status: %d/%d",
            len([k for k, v in results.items() if v]),
            len(channel_ids),
        )
        return results

    async def get_videos(
        self,
        channel_id: str,
        page: int = 1,
        page_size: int = 30,
        status_filter: Optional[str] = None,
    ) -> PaginatedVideos:
        credential = _create_credential()
        if not credential:
            return PaginatedVideos(
                videos=[], total=0, page=page, page_size=page_size, total_pages=0
            )

        try:
            u = user.User(uid=int(channel_id), credential=credential)
            videos_data = await u.get_videos(pn=page, ps=page_size)

            list_data = videos_data.get("list", {})
            vlist = list_data.get("vlist", [])

            videos = []
            for v in vlist:
                pubdate = None
                try:
                    pubdate = datetime.fromtimestamp(
                        v.get("pubdate", 0), tz=timezone.utc
                    )
                except Exception:
                    pass

                videos.append(
                    VideoItem(
                        id=str(v.get("aid", "")),
                        title=v.get("title", ""),
                        thumbnail_url=v.get("pic"),
                        duration=self._format_duration(v.get("length")),
                        view_count=v.get("play", 0),
                        published_at=pubdate,
                        status="upload",
                    )
                )

            total = list_data.get("count", 0)
            total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

            return PaginatedVideos(
                videos=videos,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )
        except Exception as e:
            logger.warning("Bilibili get_videos error: %s", e)

        return PaginatedVideos(
            videos=[], total=0, page=page, page_size=page_size, total_pages=0
        )

    def _format_duration(self, duration_str: Optional[str]) -> Optional[str]:
        if not duration_str:
            return None

        if ":" in duration_str:
            return duration_str

        try:
            seconds = int(duration_str)
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes}:{seconds:02d}"
        except Exception:
            return duration_str

    def generate_embed_url(self, video_id: str) -> str:
        vid = self.normalize_video_id(video_id)
        return f"https://player.bilibili.com/player.html?bvid={vid}&autoplay=0"

    def normalize_video_id(self, video_id: str) -> str:
        if not video_id:
            return ""

        if video_id.startswith("BV"):
            return video_id

        if video_id.startswith("https://") or video_id.startswith("http://"):
            if "bvid=" in video_id:
                import re

                match = re.search(r"bvid=([A-Za-z0-9]{10})", video_id)
                if match:
                    return match.group(1)
            if "/video/" in video_id:
                import re

                match = re.search(r"/video/([A-Za-z0-9]{10})", video_id)
                if match:
                    return match.group(1)

        return video_id


bilibili_platform = BilibiliPlatform()
