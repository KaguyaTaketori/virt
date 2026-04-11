from __future__ import annotations

import asyncio
import html
import re
from datetime import datetime, timezone
from functools import lru_cache
from typing import FrozenSet, Optional

import httpx
from fastapi import Depends
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.database import upsert
from app.loguru_config import logger
from app.models.models import Channel, Platform, Video
from app.services.api_key_manager import get_api_key, is_api_available

YT_API_BASE = "https://www.googleapis.com/youtube/v3"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

BATCH_SIZE = 50
HTTP_TIMEOUT = 20.0

_column_cache_lock = asyncio.Lock()
_column_cache: dict[str, FrozenSet[str]] = {}

PREMIERE_POSITIVE_THRESHOLD = 60
YT_LIVE_STRONG = 14400
YT_LIVE_THRESHOLD = 7200
YT_PREMIERE_LONG = 3600
YT_PREMIERE_MEDIUM = 600
YT_PREMIERE_SHORT = 120
YT_SHORT_MAX_SECS = 60

PREMIERE_TITLE_KWS = re.compile(
    r"\b(mv|official video|cover|premiere|trailer|teaser|lyric video)\b|翻唱|首播|原创|动画",
    re.IGNORECASE,
)
LIVE_TITLE_KWS = re.compile(
    r"\b(live|stream|chat|freechat)\b|🔴|直播|歌枠|杂谈|vtuber|耐久|アーカイブ",
    re.IGNORECASE,
)
PREMIERE_DESC_KWS = re.compile(
    r"\b(vocal|mix|illust|movie|director|music|arrangement)\s*[:：]", re.IGNORECASE
)
LIVE_DESC_KWS = re.compile(
    r"\b(superchat|rules|streamlabs)\b|直播规则|聊天室规则|ルール", re.IGNORECASE
)


class YouTubeClient:
    """
    YouTube API 客户端，整合解析、同步、频道解析功能。
    可通过 Depends 注入到 FastAPI 路由。
    """

    def _clean_youtube_url(self, extracted_url: str) -> str:
        if not extracted_url:
            return extracted_url
        return extracted_url.replace("\\u0026", "&").replace("\\/", "/")

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except Exception:
            return None

    def _parse_duration(self, iso_duration: Optional[str]) -> tuple[Optional[str], int]:
        if not iso_duration:
            return None, 0

        match = re.fullmatch(
            r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration
        )
        if not match:
            return None, 0

        days = int(match.group(1) or 0)
        hours = int(match.group(2) or 0) + days * 24
        minutes = int(match.group(3) or 0)
        seconds = int(match.group(4) or 0)

        total_secs = hours * 3600 + minutes * 60 + seconds

        if hours > 0:
            fmt = f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            fmt = f"{minutes}:{seconds:02d}"

        return fmt, total_secs

    def _is_premiere_heuristic(self, item: dict, total_secs: int) -> bool:
        score = 0
        snippet = item.get("snippet", {})
        title = snippet.get("title", "")
        description = snippet.get("description", "")
        category_id = snippet.get("categoryId", "")

        if total_secs < YT_PREMIERE_SHORT:
            score += 80
        elif total_secs < YT_PREMIERE_MEDIUM:
            score += 40
        elif total_secs < YT_PREMIERE_LONG:
            score += 20
        elif total_secs > YT_LIVE_STRONG:
            score -= 80
        elif total_secs > YT_LIVE_THRESHOLD:
            score -= 40

        if PREMIERE_TITLE_KWS.search(title):
            score += 30
        if LIVE_TITLE_KWS.search(title):
            score -= 40

        if PREMIERE_DESC_KWS.search(description):
            score += 30
        if LIVE_DESC_KWS.search(description):
            score -= 40

        if category_id == "10":
            score += 20
        elif category_id == "20":
            score -= 15

        return score > PREMIERE_POSITIVE_THRESHOLD

    def _determine_video_status(self, item: dict, total_secs: int) -> str:
        snippet = item.get("snippet", {})
        live_content = snippet.get("liveBroadcastContent", "none")
        live_details = item.get("liveStreamingDetails", {})

        if live_content == "live":
            return "live"
        if live_content == "upcoming":
            return "upcoming"

        if live_details.get("actualEndTime"):
            is_premiere = self._is_premiere_heuristic(item, total_secs)
            return "upload" if is_premiere else "archive"

        if 0 < total_secs <= YT_SHORT_MAX_SECS:
            return "short"

        return "upload"

    def _extract_thumbnail(self, snippet: dict) -> Optional[str]:
        thumbs = snippet.get("thumbnails", {})
        for quality in ("maxres", "standard", "high", "medium", "default"):
            url = thumbs.get(quality, {}).get("url")
            if url:
                return url
        return None

    def parse_video_item(
        self, channel_id: int, channel_platform: str, item: dict
    ) -> dict:
        """将 YouTube API 的 video item 解析为可直接用于 Upsert 的字段字典"""
        video_id = item["id"]
        snippet = item.get("snippet", {})
        content = item.get("contentDetails", {})
        stats = item.get("statistics", {})
        live = item.get("liveStreamingDetails") or {}

        duration_fmt, total_secs = self._parse_duration(content.get("duration"))
        status = self._determine_video_status(item, total_secs)

        return {
            "channel_id": channel_id,
            "platform": channel_platform,
            "video_id": video_id,
            "title": snippet.get("title"),
            "thumbnail_url": self._extract_thumbnail(snippet),
            "duration": duration_fmt,
            "duration_secs": total_secs if total_secs > 0 else None,
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats["likeCount"]) if stats.get("likeCount") else None,
            "status": status,
            "published_at": self._parse_datetime(snippet.get("publishedAt")),
            "scheduled_at": self._parse_datetime(live.get("scheduledStartTime")),
            "live_started_at": self._parse_datetime(live.get("actualStartTime")),
            "live_ended_at": self._parse_datetime(live.get("actualEndTime")),
            "live_chat_id": live.get("activeLiveChatId"),
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, max=30))
    async def get_channel_info(self, channel_id: str) -> Optional[dict]:
        """获取频道基本信息，带重试"""
        if not channel_id or not channel_id.startswith("UC"):
            return None

        if await is_api_available():
            api_key = await get_api_key()
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"{YT_API_BASE}/channels",
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

    def _parse_channel_api_response(self, item: dict, channel_id: str) -> dict:
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

        return {
            "platform": Platform.YOUTUBE,
            "channel_id": channel_id,
            "name": snippet.get("title", ""),
            "avatar_url": avatar_url,
            "banner_url": banner_url,
            "description": description,
            "youtube_url": f"https://www.youtube.com/channel/{channel_id}",
        }

    async def _get_channel_info_fallback(self, channel_id: str) -> Optional[dict]:
        url = f"https://www.youtube.com/channel/{channel_id}"
        try:
            async with httpx.AsyncClient(
                timeout=10.0, follow_redirects=True, max_redirects=3
            ) as client:
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
                    return {
                        "platform": Platform.YOUTUBE,
                        "channel_id": channel_id,
                        "name": title or "",
                        "avatar_url": avatar_url,
                    }
        except Exception as e:
            logger.debug("Scraping channel info error: %s", e)
        return None

    async def resolve_channel_id(self, input_str: str) -> Optional[str]:
        """从URL/handle解析出频道ID"""
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
            async with httpx.AsyncClient(
                timeout=10.0, follow_redirects=True, max_redirects=3
            ) as client:
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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, max=30))
    async def get_live_status(self, channel_id: str) -> Optional[dict]:
        """获取单个频道的直播状态，带重试"""
        if not await is_api_available():
            return None

        api_key = await get_api_key()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{YT_API_BASE}/search",
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
                        return {
                            "video_id": item.get("id", {}).get("videoId"),
                            "title": snippet.get("title"),
                            "thumbnail_url": snippet.get("thumbnails", {})
                            .get("high", {})
                            .get("url"),
                            "status": "live",
                            "viewer_count": 0,
                            "started_at": self._parse_datetime(
                                snippet.get("publishedAt")
                            ),
                        }
        except Exception as e:
            logger.warning("YouTube live status error: %s", e)

        return {
            "video_id": None,
            "title": None,
            "thumbnail_url": None,
            "status": "offline",
            "viewer_count": 0,
        }

    async def batch_get_live_status(
        self, channel_ids: list[str], max_concurrent: int = 5
    ) -> dict[str, Optional[dict]]:
        """批量获取多个频道的直播状态"""
        import random

        if not channel_ids:
            return {}

        semaphore = asyncio.Semaphore(max_concurrent)
        results: dict[str, Optional[dict]] = {}

        async def fetch_with_limit(cid: str) -> tuple[str, Optional[dict]]:
            async with semaphore:
                await asyncio.sleep(random.uniform(0.5, 1.5))
                status = await self.get_live_status(cid)
                return cid, status

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

    def _uc_to_uu(self, channel_id: str) -> Optional[str]:
        if channel_id and channel_id.startswith("UC"):
            return "UU" + channel_id[2:]
        return None

    async def _get_real_uploads_playlist_id(
        self, client: httpx.AsyncClient, api_key: str, channel_id: str
    ) -> Optional[str]:
        params = {"key": api_key, "part": "contentDetails", "id": channel_id}
        try:
            resp = await client.get(
                f"{YT_API_BASE}/channels", params=params, timeout=HTTP_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            if items:
                playlist_id = (
                    items[0]
                    .get("contentDetails", {})
                    .get("relatedPlaylists", {})
                    .get("uploads")
                )
                if playlist_id:
                    return playlist_id
        except Exception as e:
            logger.error(
                "API 获取频道 uploads playlist 失败 channel_id={}: {}", channel_id, e
            )
        return None

    async def get_playlist_total_videos(
        self, client: httpx.AsyncClient, api_key: str, playlist_id: str
    ) -> Optional[int]:
        params = {"key": api_key, "part": "contentDetails", "id": playlist_id}
        try:
            resp = await client.get(
                f"{YT_API_BASE}/playlists", params=params, timeout=HTTP_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            if items:
                return items[0].get("contentDetails", {}).get("itemCount", 0)
        except Exception as e:
            logger.error(
                "API 获取播放列表视频数失败 playlist_id={}: {}", playlist_id, e
            )
        return None

    async def is_channel_full_sync_completed(
        self, session: AsyncSession, channel: Channel, api_key: str
    ) -> bool:
        async with httpx.AsyncClient() as client:
            playlist_id = self._uc_to_uu(channel.channel_id)
            if not playlist_id:
                playlist_id = await self._get_real_uploads_playlist_id(
                    client, api_key, channel.channel_id
                )

            if not playlist_id:
                return False

            total_videos = await self.get_playlist_total_videos(
                client, api_key, playlist_id
            )
            if total_videos is None:
                return False

            result = await session.execute(
                select(Video).where(Video.channel_id == channel.id)
            )
            db_count = len(result.scalars().all())

            return db_count >= total_videos

    async def _get_table_columns(
        self, session: AsyncSession, model_class
    ) -> FrozenSet[str]:
        table_name = model_class.__tablename__

        if table_name not in _column_cache:
            async with _column_cache_lock:
                if table_name not in _column_cache:
                    cols = frozenset(
                        c.key for c in inspect(model_class).mapper.column_attrs
                    )
                    _column_cache[table_name] = cols

        return _column_cache[table_name]

    async def _load_existing_video_id_set(
        self, session: AsyncSession, channel_id: int
    ) -> set[str]:
        result = await session.execute(
            select(Video.video_id).where(Video.channel_id == channel_id)
        )
        return set(result.scalars().all())

    async def _upsert_video(
        self,
        session: AsyncSession,
        *,
        existing_video_ids: set[str],
        video_data: dict,
    ) -> None:
        db_video_columns = await self._get_table_columns(session, Video)

        safe_data = {k: v for k, v in video_data.items() if k in db_video_columns}
        safe_data["fetched_at"] = datetime.now(timezone.utc)

        update_cols = {
            k: v
            for k, v in safe_data.items()
            if k not in ["id", "channel_id", "video_id", "platform"]
        }

        await upsert(
            session,
            Video,
            values=safe_data,
            index_elements=["channel_id", "video_id"],
            update_cols=update_cols,
        )
        existing_video_ids.add(video_data["video_id"])

    async def _fetch_playlist_page(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        playlist_id: str,
        page_token: Optional[str] = None,
    ) -> tuple[list[str], Optional[str], Optional[int]]:
        params = {
            "key": api_key,
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": BATCH_SIZE,
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            resp = await client.get(
                f"{YT_API_BASE}/playlistItems", params=params, timeout=HTTP_TIMEOUT
            )
            if resp.status_code != 200:
                return [], None, resp.status_code

            data = resp.json()
            video_ids = [
                item["snippet"]["resourceId"]["videoId"]
                for item in data.get("items", [])
                if item.get("snippet", {}).get("resourceId", {}).get("kind")
                == "youtube#video"
            ]
            return video_ids, data.get("nextPageToken"), 200
        except Exception as e:
            logger.error("PlaylistItems.list 请求异常: {}", e)
            return [], None, None

    async def _fetch_video_details_batch(
        self, client: httpx.AsyncClient, api_key: str, video_ids: list[str]
    ) -> list[dict]:
        if not video_ids:
            return []

        params = {
            "key": api_key,
            "part": "snippet,contentDetails,statistics,liveStreamingDetails",
            "id": ",".join(video_ids),
        }
        try:
            resp = await client.get(
                f"{YT_API_BASE}/videos", params=params, timeout=HTTP_TIMEOUT
            )
            if resp.status_code != 200:
                return []
            return resp.json().get("items", [])
        except Exception as e:
            logger.error("Videos.list 请求异常: {}", e)
            return []

    async def sync_channel_videos(
        self,
        session: AsyncSession,
        channel: Channel,
        api_key: str,
        full_refresh: bool = False,
    ) -> int:
        """同步频道视频，返回新增/更新数量"""
        existing_video_ids = await self._load_existing_video_id_set(session, channel.id)

        total_processed = 0
        page_token: Optional[str] = None
        playlist_id = self._uc_to_uu(channel.channel_id)

        async with httpx.AsyncClient() as client:
            while True:
                video_ids, next_token, status = await self._fetch_playlist_page(
                    client, api_key, playlist_id, page_token
                )

                if status != 200 and page_token is None:
                    logger.warning(
                        "播放列表 ID {} 验证失败(status={})，尝试获取真实 uploads ID...",
                        playlist_id,
                        status,
                    )
                    playlist_id = await self._get_real_uploads_playlist_id(
                        client, api_key, channel.channel_id
                    )

                    if not playlist_id:
                        logger.error(
                            "无法获取频道 %s 的任何有效播放列表，同步终止",
                            channel.channel_id,
                        )
                        break

                    video_ids, next_token, status = await self._fetch_playlist_page(
                        client, api_key, playlist_id, page_token
                    )

                if not video_ids:
                    break

                for i in range(0, len(video_ids), BATCH_SIZE):
                    batch_ids = video_ids[i : i + BATCH_SIZE]
                    items = await self._fetch_video_details_batch(
                        client, api_key, batch_ids
                    )

                    for item in items:
                        video_data = self.parse_video_item(
                            channel.id, channel.platform.value, item
                        )
                        await self._upsert_video(
                            session,
                            existing_video_ids=existing_video_ids,
                            video_data=video_data,
                        )
                        total_processed += 1

                    await session.flush()

                if not full_refresh or not next_token:
                    break

                page_token = next_token

        channel.videos_last_fetched = datetime.now(timezone.utc)
        await session.commit()

        logger.info(
            "频道 %r 同步任务完成 | 平台: %s | 新增/更新视频数: %d | 模式: %s",
            channel.name,
            channel.platform,
            total_processed,
            "全量" if full_refresh else "仅增量(第一页)",
        )
        return total_processed

    async def fetch_and_upsert_single_video(
        self,
        session: AsyncSession,
        channel: Channel,
        video_id: str,
        api_key: str,
    ) -> Optional[dict]:
        async with httpx.AsyncClient() as client:
            items = await self._fetch_video_details_batch(client, api_key, [video_id])

        if not items:
            return None

        existing_video_ids = await self._load_existing_video_id_set(session, channel.id)
        video_data = self.parse_video_item(channel.id, channel.platform.value, items[0])

        await self._upsert_video(
            session,
            existing_video_ids=existing_video_ids,
            video_data=video_data,
        )
        await session.commit()
        return video_data

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


@lru_cache
def get_youtube_client() -> YouTubeClient:
    """获取 YouTubeClient 单例，用于 FastAPI 依赖注入"""
    return YouTubeClient()


def youtube_client_dep(
    client: YouTubeClient = Depends(get_youtube_client),
) -> YouTubeClient:
    """FastAPI 依赖注入函数"""
    return client
