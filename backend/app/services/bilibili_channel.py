from __future__ import annotations

import asyncio
from typing import Optional
from bilibili_api import user, Credential, video, dynamic

from app.config import settings
from app.loguru_config import logger


class BilibiliChannelService:
    def __init__(self, credential: Optional[Credential] = None):
        self._credential = credential

    @property
    def credential(self) -> Optional[Credential]:
        if not self._credential and settings.bilibili_sessdata:
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
            dynamics = await u.get_dynamics(offset=0, size=limit)
            result = []
            for d in dynamics:
                item = self._parse_dynamic(d)
                if item:
                    result.append(item)
            return result
        except Exception as e:
            logger.error("Failed to get dynamics, uid={}: {}", uid, e)
            return []

    def _parse_dynamic(self, d: dict) -> Optional[dict]:
        """解析动态项"""
        try:
            card_str = d.get("card", "{}")
            import json

            card = json.loads(card_str) if isinstance(card_str, str) else card_str

            dtype = d.get("type", 0)
            desc = d.get("desc", {})

            item = {
                "id": desc.get("uid"),
                "dynamic_id": desc.get("dynamic_id"),
                "type": dtype,
                "timestamp": desc.get("timestamp"),
                "content": "",
                "images": [],
                "repost_content": None,
            }

            if dtype == 2:
                item["content"] = card.get("item", {}).get("content", "")
                images = card.get("item", {}).get("pictures", [])
                item["images"] = [img.get("img_src", "") for img in images]
            elif dtype == 4:
                item["content"] = card.get("item", {}).get("content", "")
            elif dtype == 8:
                item["content"] = card.get("title", "")
                item["images"] = [card.get("pic", "")]
            elif dtype == 64:
                item["content"] = card.get("title", "")
                item["images"] = [card.get("pic", "")]
            elif dtype == 1:
                item["content"] = card.get("item", {}).get("content", "")
                if card.get("origin"):
                    origin = json.loads(card["origin"])
                    item["repost_content"] = origin.get("item", {}).get("content", "")

            return item
        except Exception as e:
            logger.warning("Failed to parse dynamic: {}", e)
            return None

    async def get_videos(self, uid: str, page: int = 1, page_size: int = 30) -> list:
        """获取用户投稿视频列表"""
        if not self.credential:
            logger.warning("No credential available for get_videos, uid={}", uid)
            return []

        try:
            u = user.User(uid=int(uid), credential=self.credential)
            videos = await u.get_videos(pn=page, ps=page_size)
            result = []
            for v in videos:
                result.append(
                    {
                        "bvid": v.get("bvid"),
                        "title": v.get("title"),
                        "pic": v.get("pic"),
                        "aid": v.get("aid"),
                        "duration": v.get("duration"),
                        "pubdate": v.get("pubdate"),
                        "play": v.get("play"),
                        "like": v.get("like"),
                        "coin": v.get("coin"),
                        "favorite": v.get("favorite"),
                        "share": v.get("share"),
                        "reply": v.get("reply"),
                    }
                )
            return result
        except Exception as e:
            logger.error("Failed to get videos, uid={}: {}", uid, e)
            return []


bilibili_channel_service = BilibiliChannelService()
