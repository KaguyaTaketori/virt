from __future__ import annotations

from abc import ABC, abstractmethod
import re
import html
import json
from typing import Optional, List, Dict
from bilibili_api import user, Credential

from app.config import settings
from app.loguru_config import logger


# ── 内容节点构建工具 ──────────────────────────────────────────────────────────
def build_content_nodes(raw_text: str, emoji_map: dict[str, str]) -> list[dict]:
    """将含表情符号的原始文本转换为节点列表。"""
    if not raw_text:
        return []
    nodes = []
    for part in re.split(r'(\[.*?\])', raw_text):
        if not part:
            continue
        if part in emoji_map:
            nodes.append({"type": "emoji", "text": part, "url": emoji_map[part]})
        else:
            nodes.append({"type": "text", "text": part})
    return nodes


def extract_emoji_map(display: dict) -> dict[str, str]:
    """从 display 字段提取表情包映射。"""
    emoji_details = (display.get("emoji_info") or {}).get("emoji_details") or []
    return {
        em["emoji_name"]: em["url"]
        for em in emoji_details
        if em.get("emoji_name") and em.get("url")
    }


class DynamicParser(ABC):
    """每种动态类型对应一个解析器，SRP 原则。"""

    @abstractmethod
    def parse(self, card: dict, card_item: dict, emoji_map: dict) -> dict:
        """返回包含 content_nodes, images, repost_content 的字典。"""

class TextDynamicParser(DynamicParser):
    """dtype=4: 纯文字动态"""
    def parse(self, card, card_item, emoji_map):
        return {
            "content_nodes": build_content_nodes(
                card_item.get("content", ""), emoji_map
            ),
            "images": [],
            "repost_content": None,
        }
    
class ImageDynamicParser(DynamicParser):
    """dtype=2: 图文动态"""
    def parse(self, card, card_item, emoji_map):
        pics = card_item.get("pictures") or []
        return {
            "content_nodes": build_content_nodes(
                card_item.get("description", ""), emoji_map
            ),
            "images": [
                p["img_src"] for p in pics
                if isinstance(p, dict) and p.get("img_src")
            ],
            "repost_content": None,
        }
    
class VideoDynamicParser(DynamicParser):
    """dtype=8: 视频投稿"""
    def parse(self, card, card_item, emoji_map):
        text = f"{card.get('title', '')}\n{card.get('desc', '')}".strip()
        return {
            "content_nodes": build_content_nodes(text, emoji_map),
            "images": [],
            "repost_content": None,
        }

class RepostDynamicParser(DynamicParser):
    """dtype=1: 转发动态"""
    def parse(self, card, card_item, emoji_map):
        origin_str = card.get("origin")
        repost_content = None
        if origin_str:
            try:
                origin_card = (
                    json.loads(origin_str)
                    if isinstance(origin_str, str) else origin_str
                )
                o_item = origin_card.get("item", {})
                repost_content = (
                    o_item.get("description")
                    or o_item.get("content")
                    or "[转发内容解析失败]"
                )
            except (json.JSONDecodeError, AttributeError):
                repost_content = "[转发内容解析失败]"

        return {
            "content_nodes": build_content_nodes(
                card_item.get("content", ""), emoji_map
            ),
            "images": [],
            "repost_content": repost_content,
        }

class FallbackDynamicParser(DynamicParser):
    """未知 dtype 的兜底解析器"""
    def parse(self, card, card_item, emoji_map):
        return {"content_nodes": [], "images": [], "repost_content": None}
    
_PARSER_REGISTRY: dict[int, DynamicParser] = {
    1: RepostDynamicParser(),
    2: ImageDynamicParser(),
    4: TextDynamicParser(),
    8: VideoDynamicParser(),
}
_FALLBACK_PARSER = FallbackDynamicParser()


def get_parser(dtype: int) -> DynamicParser:
    return _PARSER_REGISTRY.get(dtype, _FALLBACK_PARSER)

class BilibiliChannelService:
    def __init__(self, credential: Optional[Credential] = None):
        self._credential = credential
        self._user_credential: Optional[Credential] = None

    def set_user_credential(
        self,
        sessdata: str,
        bili_jct: str,
        buvid3: str,
        dedeuserid: Optional[str] = None,
    ) -> None:
        try:
            self._user_credential = Credential(
                sessdata=sessdata,
                bili_jct=bili_jct,
                buvid3=buvid3,
                dedeuserid=dedeuserid,
            )
            logger.info("User credential set successfully")
        except Exception as e:
            logger.warning("Failed to create user credential: {}", e)
            self._user_credential = None

    @property
    def credential(self) -> Optional[Credential]:
        if self._user_credential:
            return self._user_credential
        if self._credential:
            return self._credential
        if settings.bilibili_sessdata:
            try:
                self._credential = Credential(sessdata=settings.bilibili_sessdata)
            except Exception as e:
                logger.warning("Failed to create Bilibili credential: {}", e)
        return self._credential

    async def get_info(self, uid: str) -> Optional[dict]:
        """获取用户主页信息"""
        if not self.credential:
            logger.warning("No credential available for get_info, uid={}", uid)
            return None

        try:
            u = user.User(uid=int(uid), credential=self.credential)
            info = await u.get_user_info()
            return {
                "mid": info.get("mid"),
                "name": info.get("name"),
                "sex": info.get("sex"),
                "face": info.get("face"),
                "sign": info.get("sign"),
                "level": info.get("level"),
                "fans": info.get("fans"),
                "attention": info.get("attention"),
                "archive_count": info.get("archive_count"),
                "article_count": info.get("article_count"),
                "following": info.get("following"),
                "like_num": info.get("like_num"),
                "official_verify": info.get("official_verify"),
            }
        except Exception as e:
            logger.error("Failed to get user info, uid={}: {}", uid, e)
            return None

    async def get_dynamics(self, uid: str, limit: int = 30) -> list:
        """获取用户动态列表"""
        if not self.credential:
            logger.warning("No credential available for get_dynamics, uid={}", uid)
            return []

        try:
            u = user.User(uid=int(uid), credential=self.credential)
            dynamics = await u.get_dynamics(offset=0)
            result = []
            for d in dynamics.get("cards", []):
                item = self._parse_dynamic(d)
                if item:
                    result.append(item)
            return result[:limit]
        except Exception as e:
            logger.error("Failed to get dynamics, uid={}: {}", uid, e)
            return []



    def _parse_dynamic(self, d: dict) -> Optional[dict]:
        try:
            desc = d.get("desc", {})
            display = d.get("display", {})
            card_raw = d.get("card", {})
            card = json.loads(card_raw) if isinstance(card_raw, str) else card_raw
            card_item = card.get("item") or {}
            dtype = desc.get("type", 0)

            emoji_map = extract_emoji_map(display)
            parser = get_parser(dtype)
            parsed_content = parser.parse(card, card_item, emoji_map)

            return {
                "dynamic_id": desc.get("dynamic_id_str") or str(desc.get("dynamic_id", "")),
                "uid": desc.get("uid"),
                "uname": desc.get("user_profile", {}).get("info", {}).get("uname", ""),
                "type": dtype,
                "timestamp": desc.get("timestamp"),
                **parsed_content,  # content_nodes, images, repost_content
            }
        except Exception as e:
            logger.warning(
                "解析动态项失败: {} | dynamic_id={}",
                e,
                d.get("desc", {}).get("dynamic_id", "unknown")
            )
            return None
        
    async def get_videos(self, uid: str, page: int = 1, page_size: int = 30) -> list:
        """获取用户投稿视频列表"""
        if not self.credential:
            logger.warning("No credential available for get_videos, uid={}", uid)
            return []

        try:
            u = user.User(uid=int(uid), credential=self.credential)
            videos_data = await u.get_videos(pn=page, ps=page_size)

            vlist = (videos_data.get("list") or {}).get("vlist") or []
            
            result = []
            for v in vlist:
                result.append({
                    "bvid": v.get("bvid"),
                    "title": v.get("title"),
                    "pic": v.get("pic"),
                    "aid": v.get("aid"),
                    "duration": v.get("length"),
                    "pubdate": v.get("created"),
                    "play": v.get("play"),
                    "like": (v.get("stat") or {}).get("like", 0), 
                    "reply": v.get("comment", 0),
                })
            return result
        except Exception as e:
            logger.error("Failed to get videos, uid={}: {}", uid, e)
            return []


bilibili_channel_service = BilibiliChannelService()
