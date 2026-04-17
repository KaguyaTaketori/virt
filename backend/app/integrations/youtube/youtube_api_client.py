import httpx
import re
from typing import Optional, List, Tuple, Dict, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.exceptions import YouTubeAPIError
from app.loguru_config import logger
from app.services.api_key_manager import get_api_key, is_api_available
from app.deps import get_quota_dep
from app.integrations.urls import validate_safe_url

YT_API_BASE = "https://www.googleapis.com/youtube/v3"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HTTP_TIMEOUT = 20.0


class YouTubeApiClient:
    """
    YouTube API 客户端：负责所有 HTTP 请求、重试逻辑、配额检查。
    不涉及复杂的业务解析逻辑。
    """

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any],
        use_quota: Optional[Tuple[str, int]] = None,
    ) -> Dict[str, Any]:
        """通用请求方法，处理 API Key 和配额"""
        if not await is_api_available():
            raise YouTubeAPIError("API quota not available", platform="youtube")

        # 如果需要检查配额
        if use_quota:
            q_name, q_cost = use_quota
            if not await get_quota_dep().can_spend(q_name, q_cost):
                raise YouTubeAPIError(
                    f"Quota exhausted for {q_name}", platform="youtube"
                )

        api_key = await get_api_key()
        params["key"] = api_key

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.request(
                method, f"{YT_API_BASE}/{endpoint}", params=params
            )

            if resp.status_code != 200:
                logger.warning("YouTube API {} Error: {}", endpoint, resp.status_code)
                return {}

            if use_quota:
                await get_quota_dep().spend(use_quota[0], use_quota[1])

            return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, max=30))
    async def get_channel_info_api(self, channel_id: str) -> Optional[dict]:
        """通过 API 获取频道原始数据"""
        data = await self._request(
            "GET",
            "channels",
            {"part": "snippet,brandingSettings,contentDetails", "id": channel_id},
        )
        items = data.get("items", [])
        return items[0] if items else None

    async def get_channel_info_fallback(self, channel_id: str) -> Optional[str]:
        """通过爬虫获取频道页面 HTML (当 API 不可用或配额耗尽时)"""
        url = f"https://www.youtube.com/channel/{channel_id}"
        try:
            async with httpx.AsyncClient(
                timeout=10.0, follow_redirects=True, max_redirects=3
            ) as client:
                resp = await client.get(url, headers={"User-Agent": DEFAULT_USER_AGENT})
                return resp.text if resp.status_code == 200 else None
        except Exception as e:
            logger.debug("Scraping channel info error: {}", e)
            return None

    async def fetch_playlist_page(
        self, playlist_id: str, page_token: Optional[str] = None
    ) -> Tuple[List[str], Optional[str], Optional[int]]:
        """获取播放列表中的视频 ID 列表"""
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": 50,
        }
        if page_token:
            params["pageToken"] = page_token

        # 这里直接手动处理，因为需要捕获状态码
        api_key = await get_api_key()
        params["key"] = api_key

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                resp = await client.get(f"{YT_API_BASE}/playlistItems", params=params)
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

    async def fetch_video_details_batch(self, video_ids: List[str]) -> List[dict]:
        """批量获取视频详情数据"""
        if not video_ids:
            return []

        data = await self._request(
            "GET",
            "videos",
            {
                "part": "snippet,contentDetails,statistics,liveStreamingDetails",
                "id": ",".join(video_ids),
            },
        )
        return data.get("items", [])

    async def get_real_uploads_playlist_id(self, channel_id: str) -> Optional[str]:
        """获取频道实际的‘上传视频’播放列表 ID"""
        data = await self._request(
            "GET", "channels", {"part": "contentDetails", "id": channel_id}
        )
        items = data.get("items", [])
        if items:
            return (
                items[0]
                .get("contentDetails", {})
                .get("relatedPlaylists", {})
                .get("uploads")
            )
        return None

    async def get_playlist_total_count(self, playlist_id: str) -> Optional[int]:
        """获取播放列表包含的视频总数"""
        data = await self._request(
            "GET", "playlists", {"part": "contentDetails", "id": playlist_id}
        )
        items = data.get("items", [])
        if items:
            return items[0].get("contentDetails", {}).get("itemCount", 0)
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
    )
    async def get_live_search_result(self, channel_id: str) -> Optional[dict]:
        """通过 Search API 获取当前正在直播的项目"""
        data = await self._request(
            "GET",
            "search",
            {
                "part": "id,snippet",
                "channelId": channel_id,
                "eventType": "live",
                "type": "video",
            },
            use_quota=("search.list", 1),
        )
        items = data.get("items", [])
        return items[0] if items else None

    # --- 频道 ID 解析相关（网页爬取） ---

    async def resolve_from_url(self, url: str) -> Optional[str]:
        """从 URL 爬取页面并匹配频道 ID"""
        try:
            validate_safe_url(url, allowed_hosts={"youtube.com", "youtu.be"})
            async with httpx.AsyncClient(
                timeout=10.0, follow_redirects=True, max_redirects=3
            ) as client:
                resp = await client.get(url, headers={"User-Agent": DEFAULT_USER_AGENT})
                if resp.status_code != 200:
                    return None

                # 再次校验重定向后的 URL 安全性
                validate_safe_url(
                    str(resp.url), allowed_hosts={"youtube.com", "youtu.be"}
                )
                html_content = resp.text
        except Exception as e:
            logger.debug("Resolve from page error for {}: {}", url[:80], e)
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
