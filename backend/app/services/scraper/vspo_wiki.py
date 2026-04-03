import re
import logging
from typing import Optional
from bs4 import BeautifulSoup, Tag

from .base import BaseWikiScraper, VtuberChannel

logger = logging.getLogger(__name__)

VSPO_WIKI_URL = "https://wikiwiki.jp/vspo/%E9%85%8D%E4%BF%A1%E3%83%81%E3%83%A3%E3%83%B3%E3%83%8D%E3%83%AB%E4%B8%80%E8%A6%A7"
VSPO_ORG_NAME = "VSPO!"


class VSPOWikiScraper(BaseWikiScraper):
    """VSPO! Wiki 爬虫"""

    async def scrape(self) -> list[VtuberChannel]:
        """爬取VSPO! Wiki频道列表"""
        html = await self.fetch_page(VSPO_WIKI_URL)
        return self.parse_channels(html)

    def parse_channels(self, html: str) -> list[VtuberChannel]:
        """解析HTML获取频道列表"""
        soup = BeautifulSoup(html, "html.parser")
        channels = []

        # 找到所有h2标题
        h2_elements = soup.find_all("h2")

        for h2 in h2_elements:
            # 提取group名称（h2的文本内容）
            group = h2.get_text(strip=True)

            # 找到h2后面的表格
            next_element = h2.find_next_sibling()
            while next_element and next_element.name not in ["table", "h2"]:
                next_element = next_element.find_next_sibling()

            if next_element and next_element.name == "table":
                table_channels = self._parse_table(next_element, group)
                channels.extend(table_channels)

        # 去重
        seen = set()
        unique_channels = []
        for ch in channels:
            key = (ch.youtube_channel_id or ch.youtube_handle, ch.name)
            if key not in seen:
                seen.add(key)
                unique_channels.append(ch)

        logger.info(f"Parsed {len(unique_channels)} VSPO! channels from wiki")
        return unique_channels

    def _parse_table(self, table, group: str) -> list[VtuberChannel]:
        """解析单个表格"""
        channels = []
        rows = table.find_all("tr")

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            try:
                channel = self._parse_row(cells, group)
                if channel:
                    channels.append(channel)
            except Exception as e:
                logger.debug(f"Failed to parse row: {e}")
                continue

        return channels

    def _parse_row(self, cells, group: str) -> Optional[VtuberChannel]:
        """解析表格行"""
        name_cell = cells[0]
        name_link = name_cell.find("a")
        name = (
            name_link.get_text(strip=True)
            if name_link
            else name_cell.get_text(strip=True)
        )

        if not name:
            return None

        channel = VtuberChannel(name=name, group=group, status="active")

        for cell in cells:
            links = cell.find_all("a", href=True)
            for link in links:
                href = link.get("href", "")

                if "youtube.com" in href:
                    yt_result = self.extract_youtube_channel_id(href)
                    if yt_result[0]:
                        channel.youtube_channel_id = yt_result[0]
                    elif yt_result[1]:
                        channel.youtube_handle = yt_result[1]

                elif "twitter.com" in href or "x.com" in href:
                    channel.twitter_url = self.extract_twitter_url(href)

                elif "twitch.tv" in href:
                    channel.twitch_url = self.extract_twitch_url(href)

        if not channel.youtube_channel_id and not channel.youtube_handle:
            return None

        return channel
