from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass
import json
import re
from datetime import datetime, timezone
from typing import Optional
from bilibili_api import user, Credential

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.loguru_config import logger
from app.models.models import BilibiliDynamic, Video, Platform

MAX_RETRIES = 3
BACKOFF_INIT = 2
BACKOFF_MAX = 60


@dataclass(frozen=True)
class BilibiliContext:
    """封装单次请求的不可变上下文，线程安全"""

    credential: Optional[Credential]
    db: AsyncSession
    channel_id: int


DYNAMIC_TYPE_MAP = {
    "DYNAMIC_TYPE_NONE": 0,
    "DYNAMIC_TYPE_FORWARD": 1,
    "DYNAMIC_TYPE_DRAW": 2,
    "DYNAMIC_TYPE_PIC": 2,
    "DYNAMIC_TYPE_TEXT": 4,
    "DYNAMIC_TYPE_VIDEO": 8,
    "DYNAMIC_TYPE_ARTICLE": 4,
    "DYNAMIC_TYPE_OPUS": 2,
    "DYNAMIC_TYPE_AV": 8,
    "DYNAMIC_TYPE_UGC_SEASON": 16,
    "DYNAMIC_TYPE_MUSIC": 32,
    "DYNAMIC_TYPE_LIVE": 64,
    "DYNAMIC_TYPE_COURSE": 128,
}


class BilibiliChannelService:
    def __init__(self, credential: Optional[Credential] = None):
        self._credential = credential
        self._user_credential: Optional[Credential] = None
        self._db_session: Optional[AsyncSession] = None
        self._channel_id: Optional[int] = None

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

    def set_db_context(self, db: AsyncSession, channel_id: int) -> None:
        self._db_session = db
        self._channel_id = channel_id

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

    async def update_channel(self, channel, info: dict) -> None:
        """将用户信息应用到 Channel 对象"""
        if not info:
            return
        try:
            changed = False
            if info.get("name") and channel.name != info["name"]:
                channel.name = info["name"]
                changed = True
            if info.get("face") and channel.bilibili_face != info["face"]:
                channel.bilibili_face = info["face"]
                changed = True
            if info.get("sign") and channel.bilibili_sign != info["sign"]:
                channel.bilibili_sign = info["sign"]
                changed = True
            if info.get("fans") is not None:
                channel.bilibili_fans = info["fans"]
                changed = True
            if info.get("archive_count") is not None:
                channel.bilibili_archive_count = info["archive_count"]
                changed = True
            if info.get("attention") is not None:
                channel.bilibili_following = info["attention"]
                changed = True
            if changed and self._db_session:
                await self._db_session.commit()
        except Exception as e:
            logger.warning("Failed to update channel: {}", e)

    async def get_dynamics(
        self, uid: str, offset: str = "", limit: int = 100
    ) -> tuple[list, str]:
        if not self.credential:
            logger.warning("No credential available for get_dynamics, uid={}", uid)
            return [], ""

        try:
            u = user.User(uid=int(uid), credential=self.credential)
            result = await u.get_dynamics_new(offset=offset)
            items = result.get("items", []) or []
            next_offset = result.get("offset", "") or ""

            parsed = []
            for item in items:
                p = self._parse_dynamic_new(item)
                if p:
                    parsed.append(p)
                    if self._channel_id and self._db_session:
                        await self._save_dynamic_new(self._channel_id, p, item)

            logger.info(
                "uid={} 获取 {} 条动态, next_offset={}", uid, len(parsed), next_offset
            )
            return parsed, next_offset
        except Exception as e:
            logger.error("Failed to get dynamics, uid={}: {}", uid, e)
            return [], ""

    def _parse_dynamic_new(self, d: dict) -> Optional[dict]:
        try:
            modules = d.get("modules") or {}
            module_author = modules.get("module_author") or {}
            module_dynamic = modules.get("module_dynamic") or {}
            module_stat = modules.get("module_stat") or {}
            module_tag = modules.get("module_tag") or {}

            dynamic_id = d.get("id_str", "")
            dtype_str = d.get("type", "DYNAMIC_TYPE_NONE")
            dtype = DYNAMIC_TYPE_MAP.get(dtype_str, 0)

            jump_url = d.get("basic", {}).get("jump_url", "")
            if jump_url and jump_url.startswith("//"):
                jump_url = f"https:{jump_url}"

            uid = str(module_author.get("mid", ""))
            uname = module_author.get("name", "")
            face = module_author.get("face", "")
            timestamp = int(module_author.get("pub_ts") or 0)

            is_top = (module_tag.get("text") == "置顶") or (
                module_author.get("is_top") is True
            )

            stat = {
                "forward": module_stat.get("forward", {}).get("count", 0),
                "comment": module_stat.get("comment", {}).get("count", 0),
                "like": module_stat.get("like", {}).get("count", 0),
            }

            major = module_dynamic.get("major") or {}
            content_nodes = []
            images = []
            topic_name = (module_dynamic.get("topic") or {}).get("name", "")

            if "opus" in major:
                opus = major["opus"]
                summary = opus.get("summary") or {}
                nodes = summary.get("rich_text_nodes") or []

                for n in nodes:
                    ntype = n.get("type")
                    if ntype == "RICH_TEXT_NODE_TYPE_TEXT":
                        content_nodes.append({"type": "text", "text": n.get("text")})
                    elif ntype == "RICH_TEXT_NODE_TYPE_EMOJI":
                        emoji_data = n.get("emoji") or {}
                        content_nodes.append(
                            {
                                "type": "emoji",
                                "text": n.get("text"),
                                "url": emoji_data.get("icon_url"),
                            }
                        )
                    elif ntype == "RICH_TEXT_NODE_TYPE_AT":
                        content_nodes.append(
                            {"type": "at", "text": n.get("text"), "rid": n.get("rid")}
                        )

                pics = opus.get("pics") or []
                images = [p.get("url", "") for p in pics if p.get("url")]

            elif "archive" in major:
                archive = major["archive"]
                title = archive.get("title", "")
                desc = archive.get("desc", "")
                content_nodes.append(
                    {"type": "text", "text": f"【发布视频】{title}\n{desc}".strip()}
                )
                if archive.get("cover"):
                    images = [archive.get("cover")]

            if not content_nodes:
                self_text = (module_dynamic.get("desc") or {}).get("text", "").strip()
                if self_text:
                    content_nodes.append({"type": "text", "text": self_text})

            additional = d.get("additional") or {}
            if additional.get("type") == "ADDITIONAL_TYPE_RESERVE":
                reserve = additional.get("reserve") or {}
                reserve_title = reserve.get("title", "")
                content_nodes.append(
                    {"type": "text", "text": f"\n🗓️ 直播预约：{reserve_title}"}
                )

            repost_content = None
            orig = d.get("orig")
            if orig:
                o_modules = orig.get("modules") or {}
                o_author = (o_modules.get("module_author") or {}).get(
                    "name", "未知用户"
                )
                o_dyn = o_modules.get("module_dynamic") or {}

                o_text = ""
                o_major = o_dyn.get("major") or {}
                if "opus" in o_major:
                    o_text = o_major["opus"].get("summary", {}).get("text", "")
                else:
                    o_text = (o_dyn.get("desc") or {}).get("text", "")

                repost_content = f"@{o_author}: {o_text}"

            return {
                "dynamic_id": dynamic_id,
                "url": jump_url,
                "uid": uid,
                "uname": uname,
                "face": face,
                "type": dtype,
                "timestamp": timestamp,
                "content_nodes": content_nodes,
                "images": images,
                "repost_content": repost_content,
                "stat": stat,
                "topic": topic_name,
                "is_top": is_top,
            }

        except Exception as e:
            logger.exception(
                "解析新动态项失败: id=%s, error=%s", d.get("id_str", "unknown"), str(e)
            )
            return None

    async def get_dynamics_from_db(
        self, channel_id: int, offset: int = 0, limit: int = 30
    ) -> list:
        if not self._db_session:
            return []

        try:
            query = (
                select(BilibiliDynamic)
                .where(BilibiliDynamic.channel_id == channel_id)
                .order_by(BilibiliDynamic.published_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await self._db_session.execute(query)
            dynamics = result.scalars().all()

            return [
                {
                    "dynamic_id": d.dynamic_id,
                    "uid": d.uid,
                    "uname": d.uname,
                    "face": d.face,
                    "type": d.type,
                    "timestamp": d.timestamp,
                    "content_nodes": json.loads(d.content_nodes)
                    if d.content_nodes
                    else [],
                    "images": json.loads(d.images) if d.images else [],
                    "repost_content": d.repost_content,
                    "url": d.url,
                    "stat": json.loads(d.stat) if d.stat else {},
                    "topic": d.topic,
                    "is_top": d.is_top,
                }
                for d in dynamics
            ]
        except Exception as e:
            logger.error("Failed to get dynamics from db: {}", e)
            return []

    async def _save_dynamic_new(self, channel_id: int, parsed: dict, raw: dict) -> None:
        if not self._db_session:
            return
        try:
            dynamic_id = parsed.get("dynamic_id", "")
            if not dynamic_id:
                return

            result = await self._db_session.execute(
                select(BilibiliDynamic).where(BilibiliDynamic.dynamic_id == dynamic_id)
            )
            existing = result.scalar_one_or_none()

            published = None
            ts = parsed.get("timestamp")
            if ts:
                try:
                    published = datetime.fromtimestamp(ts, tz=timezone.utc)
                except Exception:
                    pass

            content_nodes_json = json.dumps(
                parsed.get("content_nodes", []), ensure_ascii=False
            )
            images_json = json.dumps(parsed.get("images", []), ensure_ascii=False)
            stat_json = json.dumps(parsed.get("stat", {}), ensure_ascii=False)

            if existing:
                existing.uname = parsed.get("uname")
                existing.face = parsed.get("face")
                existing.type = parsed.get("type")
                existing.content_nodes = content_nodes_json
                existing.images = images_json
                existing.repost_content = parsed.get("repost_content")
                existing.timestamp = ts
                existing.published_at = published
                existing.url = parsed.get("url")
                existing.stat = stat_json
                existing.topic = parsed.get("topic")
                existing.is_top = parsed.get("is_top", False)
                existing.raw_data = json.dumps(raw, ensure_ascii=False)
                existing.fetched_at = datetime.now(timezone.utc)
            else:
                dynamic = BilibiliDynamic(
                    channel_id=channel_id,
                    dynamic_id=dynamic_id,
                    uid=parsed.get("uid"),
                    uname=parsed.get("uname"),
                    face=parsed.get("face"),
                    type=parsed.get("type"),
                    content_nodes=content_nodes_json,
                    images=images_json,
                    repost_content=parsed.get("repost_content"),
                    timestamp=ts,
                    published_at=published,
                    url=parsed.get("url"),
                    stat=stat_json,
                    topic=parsed.get("topic"),
                    is_top=parsed.get("is_top", False),
                    raw_data=json.dumps(raw, ensure_ascii=False),
                    fetched_at=datetime.now(timezone.utc),
                )
                self._db_session.add(dynamic)

            await self._db_session.commit()
        except Exception as e:
            logger.warning("Failed to save dynamic new: {}", e)

    async def get_videos(self, uid: str, page: int = 1, page_size: int = 30) -> list:
        if not self.credential:
            logger.warning("No credential available for get_videos, uid={}", uid)
            return []

        backoff = BACKOFF_INIT
        for attempt in range(MAX_RETRIES):
            try:
                u = user.User(uid=int(uid), credential=self.credential)
                videos_data = await u.get_videos(pn=page, ps=page_size)

                vlist = (videos_data.get("list") or {}).get("vlist") or []

                result = []
                for v in vlist:
                    video_data = {
                        "bvid": v.get("bvid"),
                        "title": v.get("title"),
                        "pic": v.get("pic"),
                        "aid": v.get("aid"),
                        "duration": v.get("length"),
                        "pubdate": v.get("created"),
                        "play": v.get("play"),
                        "like": (v.get("stat") or {}).get("like", 0),
                        "reply": v.get("comment", 0),
                    }
                    result.append(video_data)

                    if self._db_session and self._channel_id:
                        await self._save_video(self._channel_id, v)

                return result
            except Exception as e:
                error_msg = str(e)
                if "412" in error_msg:
                    logger.warning(
                        "触发风控 412 uid={}，退避 {}s (attempt {})",
                        uid,
                        backoff,
                        attempt + 1,
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, BACKOFF_MAX)
                else:
                    logger.error("Failed to get videos, uid={}: {}", uid, e)
                    return []

        logger.warning("uid={} 获取视频重试耗尽", uid)
        return []

    async def get_all_videos(self, uid: str, page_size: int = 30) -> list:
        if not self.credential:
            logger.warning("No credential available for get_all_videos, uid={}", uid)
            return []

        all_videos = []
        page = 1
        max_pages = 10

        for page in range(1, max_pages + 1):
            videos = await self.get_videos(uid, page=page, page_size=page_size)
            if not videos:
                break
            all_videos.extend(videos)
            logger.debug("uid={} 第 {} 页获取 {} 个视频", uid, page, len(videos))
            if len(videos) < page_size:
                break

        logger.info("uid={} 共获取 {} 个视频", uid, len(all_videos))
        return all_videos

    async def _save_video(self, channel_id: int, v: dict) -> None:
        if not self._db_session:
            return
        try:
            bvid = v.get("bvid", "")
            if not bvid:
                return

            result = await self._db_session.execute(
                select(Video).where(
                    Video.channel_id == channel_id, Video.video_id == bvid
                )
            )
            existing = result.scalar_one_or_none()

            published = None
            if v.get("created"):
                try:
                    published = datetime.fromtimestamp(v.get("created"))
                except Exception:
                    pass

            if existing:
                existing.title = v.get("title")
                existing.thumbnail_url = v.get("pic", "")
                existing.view_count = v.get("play", 0)
                existing.duration = v.get("length", "")
                existing.published_at = published
            else:
                video = Video(
                    channel_id=channel_id,
                    platform=Platform.BILIBILI,
                    video_id=bvid,
                    title=v.get("title", ""),
                    thumbnail_url=v.get("pic", ""),
                    duration=v.get("length", ""),
                    view_count=v.get("play", 0),
                    published_at=published,
                    status="archive",
                )
                self._db_session.add(video)

            await self._db_session.commit()
        except Exception as e:
            logger.warning("Failed to save video: {}", e)

    async def get_videos_from_db(
        self, channel_id: int, page: int = 1, page_size: int = 30
    ) -> list:
        if not self._db_session:
            return []

        try:
            query = (
                select(Video)
                .where(
                    Video.channel_id == channel_id,
                    Video.platform == Platform.BILIBILI,
                )
                .order_by(Video.published_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            result = await self._db_session.execute(query)
            videos = result.scalars().all()

            return [
                {
                    "bvid": v.video_id,
                    "title": v.title,
                    "pic": v.thumbnail_url,
                    "aid": 0,
                    "duration": v.duration,
                    "pubdate": int(v.published_at.timestamp()) if v.published_at else 0,
                    "play": v.view_count,
                    "like": v.like_count or 0,
                    "reply": 0,
                }
                for v in videos
            ]
        except Exception as e:
            logger.error("Failed to get videos from db: {}", e)
            return []


bilibili_channel_service = BilibiliChannelService()
