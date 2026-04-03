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

        target_groups = {"JP", "EN"}

        for h2 in soup.find_all("h2"):
            group = h2.get_text(strip=True)
            if group not in target_groups:
                continue

            group_table = self._find_next_table_by_section(h2)
            if group_table:
                table_channels = self._parse_table(group_table, group)
                channels.extend(table_channels)

        seen = set()
        unique_channels = []
        for ch in channels:
            key = (ch.youtube_channel_id or ch.youtube_handle, ch.name)
            if key not in seen:
                seen.add(key)
                unique_channels.append(ch)

        logger.info(f"Parsed {len(unique_channels)} VSPO! channels from wiki")
        return unique_channels

    def _find_next_table_by_section(self, heading) -> Optional[Tag]:
        """在h2标题所在的section中查找后续的table"""
        parent = heading.parent
        if not parent:
            return None

        heading_idx = None
        for i, child in enumerate(parent.children):
            if (
                hasattr(child, "name")
                and child.name in ["h2", "h3"]
                and child == heading
            ):
                heading_idx = i
                break

        if heading_idx is None:
            return None

        for i in range(heading_idx + 1, len(list(parent.children))):
            child = list(parent.children)[i]
            if hasattr(child, "name"):
                if child.name == "table":
                    return child
                elif child.name in ["h2", "h3"]:
                    break

        return None

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
