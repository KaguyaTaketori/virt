from __future__ import annotations

import asyncio
from typing import Optional
from bilibili_api import user, Credential, video, dynamic

from app.config import settings
from app.loguru_config import logger


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
        """解析动态项"""
        try:
            card_str = d.get("card", "{}")
            import json

            card = json.loads(card_str) if isinstance(card_str, str) else card_str

            desc = d.get("desc", {})
            dtype = desc.get("type", 0)

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
                item["content"] = (card.get("item") or {}).get("content", "")
                pictures = (card.get("item") or {}).get("pictures", [])
                item["images"] = (
                    [img.get("img_src", "") for img in pictures] if pictures else []
                )
            elif dtype == 4:
                item["content"] = (card.get("item") or {}).get("content", "")
            elif dtype == 8:
                item["content"] = card.get("title", "")
                item["images"] = [card.get("pic", "")] if card.get("pic") else []
            elif dtype == 64:
                item["content"] = card.get("title", "")
                item["images"] = [card.get("pic", "")] if card.get("pic") else []
            elif dtype == 1:
                item["content"] = (card.get("item") or {}).get("content", "")
                if card.get("origin"):
                    origin = json.loads(card["origin"])
                    item["repost_content"] = (origin.get("item") or {}).get(
                        "content", ""
                    )

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
            videos_data = await u.get_videos(pn=page, ps=page_size)
            videos = (
                videos_data.get("list", {}).get("videos", [])
                if isinstance(videos_data, dict)
                else []
            )
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
