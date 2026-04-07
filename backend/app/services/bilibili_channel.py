from __future__ import annotations

import re
import html
import json
from typing import Optional, List, Dict
from bilibili_api import user, Credential

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
        try:
            desc = d.get("desc", {})
            display = d.get("display", {})
            card_data = d.get("card", {})

            if isinstance(card_data, str):
                card = json.loads(card_data)
            else:
                card = card_data

            dtype = desc.get("type", 0)
            
            item = {
                "dynamic_id": desc.get("dynamic_id_str") or str(desc.get("dynamic_id", "")),
                "uid": desc.get("uid"),
                "uname": desc.get("user_profile", {}).get("info", {}).get("uname", ""),
                "type": dtype,
                "timestamp": desc.get("timestamp"),
                "content_nodes": [],
                "images": [],
                "repost_content": None,
            }

            emoji_details = (display.get("emoji_info") or {}).get("emoji_details") or []
            emoji_map = {}
            for em in emoji_details:
                name = em.get("emoji_name")
                url = em.get("url")
                if name and url:
                    emoji_map[name] = url

            raw_text = ""
            card_item = card.get("item") or {}
            if dtype == 2: raw_text = card_item.get("description") or ""
            elif dtype == 4: raw_text = card_item.get("content") or ""
            elif dtype == 8: raw_text = f"{card.get('title', '')}\n{card.get('desc', '')}"
            elif dtype == 1: raw_text = card_item.get("content") or ""

            if raw_text:
                pattern = r'(\[.*?\])'
                parts = re.split(pattern, raw_text)
                nodes = []
                for part in parts:
                    if not part:
                        continue
                    if part in emoji_map:
                        nodes.append({
                            "type": "emoji",
                            "text": part,
                            "url": emoji_map[part]
                        })
                    else:
                        nodes.append({
                            "type": "text",
                            "text": part
                        })
                item["content_nodes"] = nodes
            if dtype == 2:
                pics = card_item.get("pictures") or []
                item["images"] = [p.get("img_src") for p in pics if isinstance(p, dict) and p.get("img_src")]
                
            elif dtype == 1:
                origin_str = card.get("origin")
                if origin_str:
                    try:
                        origin_card = json.loads(origin_str) if isinstance(origin_str, str) else origin_str
                        o_item = origin_card.get("item", {})
                        item["repost_content"] = o_item.get("description") or o_item.get("content") or ""
                    except Exception:
                        item["repost_content"] = "[转发内容解析失败]"

            return item
        except Exception as e:
            logger.error("解析动态项失败: {}, 动态ID: {}", e, desc.get("dynamic_id"))
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
