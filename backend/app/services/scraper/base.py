import re
import html
import httpx
from dataclasses import dataclass
from typing import Optional
from bs4 import BeautifulSoup

from app.config import settings
from app.loguru_config import logger

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"

DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.7,en;q=0.6",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


@dataclass
class VtuberChannel:
    """VTuber频道数据"""

    name: str
    youtube_channel_id: Optional[str] = None
    youtube_handle: Optional[str] = None
    twitter_url: Optional[str] = None
    twitch_url: Optional[str] = None
    group: Optional[str] = None
    status: Optional[str] = "active"


class BaseWikiScraper:
    """Wiki爬虫基类"""

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers=DEFAULT_HEADERS.copy(),
            follow_redirects=True,
        )

    async def close(self):
        await self.client.aclose()

    async def fetch_page(self, url: str) -> str:
        """获取页面HTML"""
        resp = await self.client.get(url)
        resp.raise_for_status()

        if "cloudflare" in resp.text.lower() or "blocked" in resp.text.lower():
            logger.warning(f"Cloudflare blocked request to {url}")
            raise Exception(
                "Cloudflare blocked - please solve CAPTCHA manually or wait"
            )

        return resp.text

    def clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""
        text = text.replace("\\u0026", "&")
        text = text.replace("\\/", "/")
        text = html.unescape(text)
        return text.strip()

    def extract_youtube_channel_id(
        self, url_or_handle: str
    ) -> tuple[Optional[str], Optional[str]]:
        """
        从YouTube URL或handle提取channel_id和handle
        返回: (channel_id, handle)
        """
        if not url_or_handle:
            return None, None

        # 处理 @username 格式
        if url_or_handle.startswith("@"):
            return None, url_or_handle

        # 处理完整URL
        # https://www.youtube.com/channel/UCxxx (24位: UC + 22字符)
        match = re.search(
            r"youtube\.com/channel/([UC][0-9a-zA-Z_-]{22}[a-zA-Z0-9_-]?)", url_or_handle
        )
        if match:
            return match.group(1), None

        # https://www.youtube.com/@username
        match = re.search(r"youtube\.com/@([a-zA-Z0-9_]+)", url_or_handle)
        if match:
            return None, f"@{match.group(1)}"

        # youtube.com/xxx (可能是handle或custom URL)
        if "youtube.com/" in url_or_handle:
            parts = url_or_handle.split("/")
            handle = parts[-1] if parts else None
            if handle and handle not in ("channel", "user", "c"):
                return None, f"@{handle}"

        return None, None

    def extract_twitter_url(self, text: str) -> Optional[str]:
        """提取Twitter/X URL"""
        if not text:
            return None
        match = re.search(
            r"https?://(?:www\.)?(twitter\.com|x\.com)/([a-zA-Z0-9_]+)", text
        )
        if match:
            return f"https://{match.group(1)}/{match.group(2)}"
        return None

    def extract_twitch_url(self, text: str) -> Optional[str]:
        """提取Twitch URL"""
        if not text:
            return None
        match = re.search(r"https?://(?:www\.)?twitch\.tv/([a-zA-Z0-9_]+)", text)
        if match:
            return f"https://www.twitch.tv/{match.group(1)}"
        return None

    def parse_html_table(self, html_text: str) -> list[list[str]]:
        """解析HTML表格"""
        soup = BeautifulSoup(html_text, "html.parser")
        table = soup.find("table")
        if not table:
            return []

        result = []
        for row in table.find_all("tr"):
            cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
            if cells:
                result.append(cells)
        return result

    async def resolve_youtube_handle(self, handle: str) -> Optional[str]:
        """
        将 @username handle 解析为 channel_id
        """
        if not handle:
            return None

        try:
            from app.services.youtube_channel import resolve_youtube_channel

            channel_id = await resolve_youtube_channel(handle)
            return channel_id
        except Exception as e:
            logger.warning(f"Failed to resolve YouTube handle {handle}: {e}")
            return None
