import re
import logging
from typing import Optional
from bs4 import BeautifulSoup, NavigableString, Tag

from .base import BaseWikiScraper, VtuberChannel

logger = logging.getLogger(__name__)

NIJISANJI_WIKI_URL = (
    "https://wikiwiki.jp/nijisanji/%E6%B4%BB%E5%8B%95%E5%A0%B4%E6%89%80/YouTube"
)
NIJISANJI_ORG_NAME = "にじさんじ"


class NijisanjiWikiScraper(BaseWikiScraper):
    """Nijisanji Wiki 爬虫"""

    async def scrape(self) -> list[VtuberChannel]:
        """爬取Nijisanji Wiki YouTube频道列表"""
        html = await self.fetch_page(NIJISANJI_WIKI_URL)
        return self.parse_channels(html)

    def parse_channels(self, html: str) -> list[VtuberChannel]:
        """解析HTML获取频道列表"""
        soup = BeautifulSoup(html, "html.parser")
        channels = []

        h3_elements = soup.find_all("h3")

        for h3 in h3_elements:
            group = h3.get_text(strip=True)
            if "出身" in group:
                group = group.replace("出身", "").strip()

            next_element = h3.find_next_sibling()
            while next_element and next_element.name not in ["ul", "h3"]:
                next_element = next_element.find_next_sibling()

            if next_element and next_element.name == "ul":
                list_channels = self._parse_list(next_element, group)
                channels.extend(list_channels)

        # 去重
        seen = set()
        unique_channels = []
        for ch in channels:
            key = (ch.youtube_channel_id or ch.youtube_handle, ch.name)
            if key not in seen:
                seen.add(key)
                unique_channels.append(ch)

        logger.info(f"Parsed {len(unique_channels)} Nijisanji channels from wiki")
        return unique_channels

    def _parse_list(self, ul, group: str) -> list[VtuberChannel]:
        """解析无序列表"""
        channels = []
        items = ul.find_all("li")

        for item in items:
            try:
                channel = self._parse_list_item(item, group)
                if channel:
                    channels.append(channel)
            except Exception as e:
                logger.debug(f"Failed to parse list item: {e}")
                continue

        return channels

    def _parse_list_item(self, item: Tag, group: str) -> Optional[VtuberChannel]:
        """解析列表项"""
        text = item.get_text(" ", strip=True)

        if "：" not in text and ":" not in text:
            return None

        delimiter = "：" if "：" in text else ":"
        parts = text.split(delimiter, 1)
        name = parts[0].strip()

        if not name:
            return None

        # 检查是否毕业（背景色为#ddd）
        wikicolor = item.find("span", class_="wikicolor")
        status = "active"
        if wikicolor:
            style = wikicolor.get("style", "")
            if "#ddd" in style or "background-color:#ddd" in style:
                status = "graduated"

        channel = VtuberChannel(name=name, group=group, status=status)

        links = item.find_all("a", href=True)
        for link in links:
            href = link.get("href", "")

            if "youtube.com" in href:
                yt_result = self.extract_youtube_channel_id(href)
                if yt_result[0]:
                    channel.youtube_channel_id = yt_result[0]
                elif yt_result[1]:
                    channel.youtube_handle = yt_result[1]

        if not channel.youtube_channel_id and not channel.youtube_handle:
            return None

        return channel
