from __future__ import annotations

import html
import math
import random
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

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
from app.services.api_key_manager import get_api_key, is_api_available

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_HTTP_CLIENT_KWARGS = {
    "timeout": 10.0,
    "follow_redirects": True,
    "max_redirects": 3,
}


class YouTubePlatform(BaseLivePlatform):
    PLATFORM = Platform.YOUTUBE

    async def get_channel_info(self, channel_id: str) -> Optional[ChannelInfo]:
        if not channel_id or not channel_id.startswith("UC"):
            return None

        if await is_api_available():
            api_key = await get_api_key()
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"{YOUTUBE_API_BASE}/channels",
                        params={
                            "part": "snippet,brandingSettings,contentDetails",
                            "id": channel_id,
                            "key": api_key,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        items = data.get("items", [])
                        if items:
                            return self._parse_channel_api_response(
                                items[0], channel_id
                            )
            except Exception as e:
                logger.warning("YouTube API Error for channel info: %s", e)

        return await self._get_channel_info_fallback(channel_id)

    def _parse_channel_api_response(self, item: dict, channel_id: str) -> ChannelInfo:
        snippet = item.get("snippet", {})
        branding = item.get("brandingSettings", {})
        thumbnails = snippet.get("thumbnails", {})
        channel_branding = branding.get("channel", {})
        image_branding = branding.get("image", {})

        avatar_url = thumbnails.get("medium", {}).get("url") or thumbnails.get(
            "default", {}
        ).get("url")
        banner_url = (
            image_branding.get("bannerTvMediumUrl")
            or image_branding.get("bannerTvUrl")
            or image_branding.get("bannerUrl")
        )
        description = channel_branding.get("description") or snippet.get("description")

        return ChannelInfo(
            platform=Platform.YOUTUBE,
            channel_id=channel_id,
            name=snippet.get("title", ""),
            avatar_url=avatar_url,
            banner_url=banner_url,
            description=description,
            youtube_url=f"https://www.youtube.com/channel/{channel_id}",
        )

    async def _get_channel_info_fallback(
        self, channel_id: str
    ) -> Optional[ChannelInfo]:
        url = f"https://www.youtube.com/channel/{channel_id}"
        try:
            async with httpx.AsyncClient(**_HTTP_CLIENT_KWARGS) as client:
                resp = await client.get(url, headers={"User-Agent": DEFAULT_USER_AGENT})
                html_text = resp.text

                title_match = re.search(r"<title>([^<]+)</title>", html_text)
                title = None
                if title_match:
                    title = html.unescape(
                        title_match.group(1).replace(" - YouTube", "").strip()
                    )

                avatar_match = re.search(
                    r'"avatar":{"thumbnails":\[{"url":"([^"]+)"', html_text
                )
                avatar_url = None
                if avatar_match:
                    avatar_url = self._clean_youtube_url(avatar_match.group(1))

                if title or avatar_url:
                    return ChannelInfo(
                        platform=Platform.YOUTUBE,
                        channel_id=channel_id,
                        name=title or "",
                        avatar_url=avatar_url,
                    )
        except Exception as e:
            logger.debug("Scraping channel info error: %s", e)
        return None

    async def resolve_channel_id(self, input_str: str) -> Optional[str]:
        if not input_str:
            return None

        input_str = input_str.strip()

        if input_str.startswith("UC") and len(input_str) >= 22:
            return input_str

        safe_url = self._build_safe_url(input_str)
        if not safe_url:
            logger.warning("Blocked unsafe channel input: %r", input_str[:50])
            return None

        try:
            channel_id = await self._resolve_from_page(safe_url)
            return channel_id
        except Exception as e:
            logger.debug("Failed to resolve channel ID from %s: %s", safe_url, e)
            return None

    def _build_safe_url(self, input_str: str) -> Optional[str]:
        if not input_str:
            return None

        input_str = input_str.strip()

        if input_str.startswith("UC") and len(input_str) >= 22:
            return f"https://www.youtube.com/channel/{input_str}"

        if input_str.startswith("@"):
            handle = input_str.lstrip("@")
            if not handle.replace("-", "").replace("_", "").replace(".", "").isalnum():
                return None
            return f"https://www.youtube.com/@{handle}"

        if input_str.startswith("http"):
            try:
                from app.integrations.urls import validate_safe_url

                return validate_safe_url(
                    input_str, allowed_hosts={"youtube.com", "youtu.be"}
                )
            except Exception:
                return None

        safe_slug = "".join(c for c in input_str if c.isalnum() or c in "-_.")
        if not safe_slug:
            return None
        return f"https://www.youtube.com/@{safe_slug}"

    async def _resolve_from_page(self, url: str) -> Optional[str]:
        from app.integrations.urls import validate_safe_url

        try:
            validate_safe_url(url, allowed_hosts={"youtube.com", "youtu.be"})
        except ValueError as e:
            logger.warning("Resolve from page blocked unsafe URL %r: %s", url[:80], e)
            return None

        try:
            async with httpx.AsyncClient(**_HTTP_CLIENT_KWARGS) as client:
                resp = await client.get(url, headers={"User-Agent": DEFAULT_USER_AGENT})
                if resp.status_code != 200:
                    return None

                final_url = str(resp.url)
                try:
                    validate_safe_url(
                        final_url, allowed_hosts={"youtube.com", "youtu.be"}
                    )
                except ValueError:
                    logger.warning("Redirect to unsafe URL blocked: %s", final_url[:80])
                    return None

                html_content = resp.text

        except Exception as e:
            logger.debug("Resolve from page error for %s: %s", url[:80], e)
            return None

        patterns = [
            r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[0-9a-zA-Z_-]{22})"',
            r'<meta property="og:url" content="https://www\.youtube\.com/channel/(UC[0-9a-zA-Z_-]{22})"',
            r'itemprop="(?:channelId|identifier)" content="(UC[0-9a-zA-Z_-]{22})"',
            r'"externalId":"(UC[0-9a-zA-Z_-]{22})"',
            r'"browseId":"(UC[0-9a-zA-Z_-]{22})"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html_content)
            if match:
                return match.group(1)

        return None

    def _clean_youtube_url(self, extracted_url: str) -> str:
        if not extracted_url:
            return extracted_url
        return extracted_url.replace("\\u0026", "&").replace("\\/", "/")

    async def get_live_status(self, channel_id: str) -> Optional[LiveStatus]:
        if not await is_api_available():
            return None

        api_key = await get_api_key()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{YOUTUBE_API_BASE}/search",
                    params={
                        "part": "id,snippet",
                        "channelId": channel_id,
                        "eventType": "live",
                        "type": "video",
                        "key": api_key,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("items", [])
                    if items:
                        item = items[0]
                        snippet = item.get("snippet", {})
                        return LiveStatus(
                            video_id=item.get("id", {}).get("videoId"),
                            title=snippet.get("title"),
                            thumbnail_url=snippet.get("thumbnails", {})
                            .get("high", {})
                            .get("url"),
                            status=LiveStatusEnum.LIVE,
                            viewer_count=0,
                            started_at=self._parse_datetime(snippet.get("publishedAt")),
                        )
        except Exception as e:
            logger.warning("YouTube live status error: %s", e)

        return LiveStatus(
            video_id=None,
            title=None,
            thumbnail_url=None,
            status=LiveStatusEnum.OFFLINE,
            viewer_count=0,
        )

    async def batch_get_live_status(
        self, channel_ids: list[str], max_concurrent: int = 5
    ) -> dict[str, Optional[LiveStatus]]:
        if not channel_ids:
            return {}

        semaphore = asyncio.Semaphore(max_concurrent)
        results: dict[str, Optional[LiveStatus]] = {}

        async def fetch_with_limit(channel_id: str) -> tuple[str, Optional[LiveStatus]]:
            async with semaphore:
                await asyncio.sleep(random.uniform(0.5, 1.5))
                status = await self.get_live_status(channel_id)
                return channel_id, status

        tasks = [fetch_with_limit(cid) for cid in channel_ids]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for item in completed:
            if isinstance(item, Exception):
                logger.error("Batch fetch error: %s", item)
                continue
            cid, status = item
            results[cid] = status

        logger.info("YouTube batch status: %d/%d", len(results), len(channel_ids))
        return results

    async def get_videos(
        self,
        channel_id: str,
        page: int = 1,
        page_size: int = 24,
        status_filter: Optional[str] = None,
    ) -> PaginatedVideos:
        if not await is_api_available():
            return PaginatedVideos(
                videos=[], total=0, page=page, page_size=page_size, total_pages=0
            )

        api_key = await get_api_key()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                search_params = {
                    "part": "id,snippet",
                    "channelId": channel_id,
                    "type": "video",
                    "order": "date",
                    "maxResults": page_size,
                    "pageToken": self._calc_page_token(page),
                    "key": api_key,
                }
                if status_filter == "live":
                    search_params["eventType"] = "live"
                elif status_filter == "upcoming":
                    search_params["eventType"] = "upcoming"

                resp = await client.get(
                    f"{YOUTUBE_API_BASE}/search", params=search_params
                )
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("items", [])
                    next_page_token = data.get("nextPageToken")

                    videos = []
                    for item in items:
                        snippet = item.get("snippet", {})
                        vid = item.get("id", {}).get("videoId")
                        if vid:
                            videos.append(
                                VideoItem(
                                    id=vid,
                                    title=snippet.get("title", ""),
                                    thumbnail_url=snippet.get("thumbnails", {})
                                    .get("high", {})
                                    .get("url"),
                                    duration=None,
                                    view_count=0,
                                    published_at=self._parse_datetime(
                                        snippet.get("publishedAt")
                                    ),
                                    status="video",
                                )
                            )

                    total = len(videos)
                    total_pages = math.ceil(total / page_size) if page_size > 0 else 0

                    return PaginatedVideos(
                        videos=videos,
                        total=total,
                        page=page,
                        page_size=page_size,
                        total_pages=total_pages,
                    )
        except Exception as e:
            logger.warning("YouTube videos error: %s", e)

        return PaginatedVideos(
            videos=[], total=0, page=page, page_size=page_size, total_pages=0
        )

    def _calc_page_token(self, page: int) -> str:
        page_token = ""
        for _ in range(page - 1):
            page_token = self._get_next_page_token(page_token)
        return page_token

    def _get_next_page_token(self, current: str) -> str:
        import base64

        if not current:
            return ""
        try:
            decoded = base64.b64decode(current.encode()).decode()
            num = int(decoded.split("_")[-1]) if "_" in decoded else 0
            new_num = num + 50
            return base64.b64encode(f"CDI{new_num}".encode()).decode()
        except Exception:
            return "CI=="

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except Exception:
            return None

    def generate_embed_url(self, video_id: str) -> str:
        vid = self.normalize_video_id(video_id)
        return f"https://www.youtube.com/embed/{vid}"

    def normalize_video_id(self, video_id: str) -> str:
        if not video_id:
            return ""

        if video_id.startswith("https://"):
            match = re.search(r"(?:v=|/v/)([a-zA-Z0-9_-]{11})", video_id)
            if match:
                return match.group(1)

        if len(video_id) == 11 and re.match(r"^[a-zA-Z0-9_-]+$", video_id):
            return video_id

        return video_id


import asyncio

youtube_platform = YouTubePlatform()
