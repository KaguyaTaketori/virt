from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Optional

from bilibili_api import user, live, Credential
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.loguru_config import logger
from app.models.models import BilibiliDynamic, Platform, Video, User

REQ_SLEEP_MIN = 1.0
REQ_SLEEP_MAX = 2.2
BATCH_SIZE = 15
BATCH_SLEEP_MIN = 3.0
BATCH_SLEEP_MAX = 5.0
BACKOFF_INIT = 2
BACKOFF_MAX = 60
MAX_RETRIES = 3


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


class BiliClient:
    """
    Bilibili API 客户端，使用 tenacity 处理重试。
    可通过 Depends 注入到 FastAPI 路由。
    """

    def _create_credential(self) -> Optional[Credential]:
        if not settings.bilibili_sessdata:
            return None
        try:
            return Credential(sessdata=settings.bilibili_sessdata)
        except Exception as e:
            logger.warning("Failed to create Bilibili credential: {}", e)
            return None

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=BACKOFF_INIT, max=BACKOFF_MAX),
    )
    async def get_user_info(
        self, uid: str, credential: Optional[Credential] = None
    ) -> Optional[dict]:
        """获取用户信息，带重试"""
        cred = credential or self._create_credential()
        if not cred:
            return None
        u = user.User(uid=int(uid), credential=cred)
        return await u.get_user_info()

    def parse_user_info(self, raw: dict) -> dict:
        """解析用户信息"""
        info = raw.get("info", {})
        detail = raw.get("detail", {})
        stats = raw.get("stat", {})
        return {
            "mid": raw.get("mid"),
            "name": info.get("uname"),
            "sex": info.get("sex"),
            "face": info.get("face"),
            "sign": detail.get("sign"),
            "level": info.get("level"),
            "fans": stats.get("follower"),
            "attention": info.get("attention"),
            "archive_count": info.get("archive", {}).get("count"),
            "article_count": info.get("article_count", 0),
            "following": info.get("following", 0),
            "like_num": info.get("like_num", 0),
            "official_verify": info.get("official_verify"),
        }

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=BACKOFF_INIT, max=BACKOFF_MAX),
    )
    async def get_live_status(
        self, uid: str, credential: Optional[Credential] = None
    ) -> Optional[dict]:
        """获取单个频道的直播状态，带重试"""
        import asyncio

        cred = credential or self._create_credential()
        if not cred:
            return None

        backoff = BACKOFF_INIT
        for attempt in range(MAX_RETRIES):
            try:
                u = user.User(uid=int(uid), credential=cred)
                user_info = await u.get_user_info()

                live_room = user_info.get("live_room")
                if not live_room:
                    return {"status": "offline"}

                room_id = live_room.get("room_id", 0)
                if not room_id:
                    return {"status": "offline"}

                room = live.LiveRoom(room_id=int(room_id), credential=cred)
                room_info = await room.get_room_info()

                if not room_info:
                    return {"status": "offline"}

                live_status = room_info.get("live_status", 0)
                if live_status == 1:
                    started_at = None
                    live_time = room_info.get("live_time")
                    if live_time:
                        try:
                            started_at = datetime.fromtimestamp(
                                int(live_time), tz=timezone.utc
                            )
                        except (ValueError, OSError, TypeError):
                            pass

                    return {
                        "video_id": str(room_info.get("room_id", "")),
                        "title": room_info.get("title"),
                        "thumbnail_url": room_info.get("user_cover")
                        or room_info.get("keyframe"),
                        "status": "live",
                        "viewer_count": room_info.get("online", 0),
                        "started_at": started_at,
                    }
                elif live_status == 2:
                    scheduled_at = None
                    live_time = room_info.get("live_time")
                    if live_time:
                        try:
                            scheduled_at = datetime.fromtimestamp(
                                int(live_time), tz=timezone.utc
                            )
                        except (ValueError, OSError, TypeError):
                            pass

                    return {
                        "video_id": str(room_info.get("room_id", "")),
                        "title": room_info.get("title"),
                        "thumbnail_url": room_info.get("user_cover"),
                        "status": "upcoming",
                        "viewer_count": 0,
                        "scheduled_at": scheduled_at,
                    }

                return {"status": "offline"}

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
                    logger.warning(
                        "获取房间信息失败 uid={} attempt={}: {}", uid, attempt + 1, e
                    )
                    await asyncio.sleep(1)

        return None

    async def batch_get_live_status(
        self, uids: list[str], max_concurrent: int = 5
    ) -> dict[str, Optional[dict]]:
        """批量获取多个频道的直播状态"""
        import asyncio

        if not uids:
            return {}

        credential = self._create_credential()
        semaphore = asyncio.Semaphore(max_concurrent)
        results: dict[str, Optional[dict]] = {}

        async def fetch_with_limit(uid: str) -> tuple[str, Optional[dict]]:
            async with semaphore:
                await asyncio.sleep(random.uniform(REQ_SLEEP_MIN, REQ_SLEEP_MAX))
                status = await self.get_live_status(uid, credential)
                return uid, status

        tasks = [fetch_with_limit(uid) for uid in uids]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for item in completed:
            if isinstance(item, Exception):
                logger.error("Batch fetch error: {}", item)
                continue
            uid, status = item
            results[uid] = status

        logger.info("Bilibili batch status: %d/%d", len(results), len(uids))
        return results

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=BACKOFF_INIT, max=BACKOFF_MAX),
    )
    async def get_dynamics(
        self, uid: str, credential: Optional[Credential], offset: str = ""
    ) -> tuple[list[dict], str]:
        """获取动态列表，带重试"""
        if not credential:
            return [], ""

        u = user.User(uid=int(uid), credential=credential)
        raw_result = await u.get_dynamics_new(offset=offset)
        raw_items = raw_result.get("items", [])

        parsed = [p for item in raw_items if (p := self._parse_dynamic(item))]

        return parsed, raw_result.get("offset", "")

    def _parse_dynamic(self, item: dict) -> Optional[dict]:
        """解析动态项"""
        try:
            modules = item.get("modules") or {}
            module_author = modules.get("module_author") or {}
            module_dynamic = modules.get("module_dynamic") or {}
            module_stat = modules.get("module_stat") or {}
            module_tag = modules.get("module_tag") or {}

            dynamic_id = item.get("id_str", "")
            dtype_str = item.get("type", "DYNAMIC_TYPE_NONE")
            dtype = DYNAMIC_TYPE_MAP.get(dtype_str, 0)

            jump_url = item.get("basic", {}).get("jump_url", "")
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

            additional = item.get("additional") or {}
            if additional.get("type") == "ADDITIONAL_TYPE_RESERVE":
                reserve = additional.get("reserve") or {}
                reserve_title = reserve.get("title", "")
                content_nodes.append(
                    {"type": "text", "text": f"\n🗓️ 直播预约：{reserve_title}"}
                )

            repost_content = None
            orig = item.get("orig")
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
                "解析新动态项失败: id=%s, error=%s",
                item.get("id_str", "unknown"),
                str(e),
            )
            return None

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=BACKOFF_INIT, max=BACKOFF_MAX),
    )
    async def get_videos(
        self,
        uid: str,
        credential: Optional[Credential],
        page: int = 1,
        page_size: int = 30,
    ) -> dict:
        """获取视频列表，带重试"""
        import asyncio

        cred = credential or self._create_credential()
        if not cred:
            return {"list": {"vlist": [], "count": 0}}

        backoff = BACKOFF_INIT
        for attempt in range(MAX_RETRIES):
            try:
                u = user.User(uid=int(uid), credential=cred)
                return await u.get_videos(pn=page, ps=page_size)
            except Exception as e:
                if "412" in str(e):
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, BACKOFF_MAX)
                else:
                    logger.error("get_videos uid={} error: {}", uid, e)
                    raise
        raise RuntimeError(f"uid={uid} 视频获取重试耗尽")

    def _parse_video(self, v: dict) -> dict:
        """解析视频项"""
        return {
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

    async def upsert_dynamics(
        self,
        db: AsyncSession,
        channel_id: int,
        parsed_dynamics: list[dict],
        raw_dynamics: list[dict],
    ) -> None:
        """将动态数据写入数据库"""
        if not parsed_dynamics:
            return

        from app.db_utils import upsert_batch, _insert_fn

        batch_values = []
        for parsed, raw in zip(parsed_dynamics, raw_dynamics):
            dynamic_id = parsed.get("dynamic_id")
            if not dynamic_id:
                continue

            ts = parsed.get("timestamp")
            batch_values.append(
                {
                    "channel_id": channel_id,
                    "dynamic_id": str(dynamic_id),
                    "uid": parsed.get("uid"),
                    "uname": parsed.get("uname"),
                    "face": parsed.get("face"),
                    "type": parsed.get("type"),
                    "content_nodes": json.dumps(
                        parsed.get("content_nodes", []), ensure_ascii=False
                    ),
                    "images": json.dumps(parsed.get("images", []), ensure_ascii=False),
                    "repost_content": parsed.get("repost_content"),
                    "timestamp": ts,
                    "published_at": datetime.fromtimestamp(ts, tz=timezone.utc)
                    if ts
                    else None,
                    "url": parsed.get("url"),
                    "stat": json.dumps(parsed.get("stat", {}), ensure_ascii=False),
                    "topic": parsed.get("topic"),
                    "is_top": parsed.get("is_top", False),
                    "raw_data": json.dumps(raw, ensure_ascii=False),
                    "fetched_at": datetime.now(timezone.utc),
                }
            )

        if batch_values:
            stmt = _insert_fn(BilibiliDynamic)
            update_cols = {
                "uname": stmt.excluded.uname,
                "face": stmt.excluded.face,
                "stat": stmt.excluded.stat,
                "is_top": stmt.excluded.is_top,
                "content_nodes": stmt.excluded.content_nodes,
                "fetched_at": stmt.excluded.fetched_at,
            }
            await upsert_batch(
                db, BilibiliDynamic, ["dynamic_id"], batch_values, update_cols
            )
            await db.commit()

    async def upsert_videos(
        self, db: AsyncSession, channel_id: int, videos: list[dict]
    ) -> None:
        """将视频数据写入数据库"""
        if not videos:
            return

        from app.db_utils import upsert_batch, _insert_fn

        batch_values = []
        for v in videos:
            bvid = v.get("bvid")
            if not bvid:
                continue

            batch_values.append(
                {
                    "channel_id": channel_id,
                    "platform": Platform.BILIBILI,
                    "video_id": bvid,
                    "title": v.get("title", ""),
                    "thumbnail_url": v.get("pic", ""),
                    "duration": v.get("length", ""),
                    "view_count": v.get("play", 0),
                    "published_at": datetime.fromtimestamp(v["created"])
                    if v.get("created")
                    else None,
                    "status": "archive",
                }
            )

        if batch_values:
            stmt = _insert_fn(Video)
            update_cols = {
                "title": stmt.excluded.title,
                "thumbnail_url": stmt.excluded.thumbnail_url,
                "view_count": stmt.excluded.view_count,
            }
            await upsert_batch(
                db, Video, ["channel_id", "video_id"], batch_values, update_cols
            )
            await db.commit()

    async def get_user_credential(
        self, user_id: int, db: AsyncSession
    ) -> Optional[dict]:
        """获取用户的 Bilibili 凭证"""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.bilibili_sessdata:
            return None

        return {
            "sessdata": user.bilibili_sessdata,
            "bili_jct": user.bilibili_bili_jct,
            "buvid3": user.bilibili_buvid3,
            "dedeuserid": user.bilibili_dedeuserid,
        }

    async def save_user_credential(
        self,
        user_id: int,
        sessdata: str,
        bili_jct: str,
        buvid3: str,
        dedeuserid: Optional[str],
        db: AsyncSession,
    ) -> bool:
        """保存用户的 Bilibili 凭证"""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False

        user.bilibili_sessdata = sessdata
        user.bilibili_bili_jct = bili_jct
        user.bilibili_buvid3 = buvid3
        user.bilibili_dedeuserid = dedeuserid

        await db.commit()
        return True

    async def delete_user_credential(self, user_id: int, db: AsyncSession) -> bool:
        """删除用户的 Bilibili 凭证"""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False

        user.bilibili_sessdata = None
        user.bilibili_bili_jct = None
        user.bilibili_buvid3 = None
        user.bilibili_dedeuserid = None

        await db.commit()
        return True

    async def get_channel_info(
        self, uid: str, credential: Optional[Credential] = None
    ) -> Optional[dict]:
        """获取频道基本信息"""
        cred = credential or self._create_credential()
        if not cred:
            return None

        try:
            u = user.User(uid=int(uid), credential=cred)
            info = await u.get_user_info()
            return self.parse_user_info(info)
        except Exception as e:
            logger.error("Failed to get user info, uid={}: {}", uid, e)
            return None


@lru_cache
def get_bili_client() -> BiliClient:
    """获取 BiliClient 单例，用于 FastAPI 依赖注入"""
    return BiliClient()


def bili_client_dep(client: BiliClient = Depends(get_bili_client)) -> BiliClient:
    """FastAPI 依赖注入函数"""
    return client
