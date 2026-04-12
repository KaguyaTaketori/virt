from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Optional

import httpx
from bilibili_api import user, live, Credential
from fastapi import Depends
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result,
)

from app.config import settings
from app.core.exceptions import BilibiliAPIError
from app.loguru_config import logger
from app.models.models import Platform
from app.schemas.schemas import BiliLiveStatus, BiliUserInfo, BiliDynamic, BiliVideo

REQ_SLEEP_MIN = 1.0
REQ_SLEEP_MAX = 2.2
MAX_CONCURRENT = 5
RETRY_MULTIPLIER = 1
RETRY_MIN = 2
RETRY_MAX = 10
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


def _is_rate_limit_error(exception: Exception) -> bool:
    error_msg = str(exception)
    return "412" in error_msg or "-509" in error_msg


def _should_retry(exception: Exception) -> bool:
    if isinstance(exception, (httpx.ConnectError, httpx.TimeoutException)):
        return True
    if _is_rate_limit_error(exception):
        return True
    return False


RETRY_CONFIG = {
    "stop": stop_after_attempt(MAX_RETRIES),
    "wait": wait_exponential(multiplier=RETRY_MULTIPLIER, min=RETRY_MIN, max=RETRY_MAX),
    "retry": retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException))
    | retry_if_result(_is_rate_limit_error),
    "reraise": True,
}

NO_RETRY_CONFIG = {
    "stop": stop_after_attempt(MAX_RETRIES),
    "wait": wait_exponential(multiplier=RETRY_MULTIPLIER, min=1, max=5),
    "retry": retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
    "reraise": True,
}


class BiliClient:
    """
    Bilibili API 客户端（去状态化版本）。
    仅负责网络请求、数据解析、异常处理。
    不直接操作数据库。
    """

    def _create_credential(self) -> Optional[Credential]:
        if not settings.bilibili_sessdata:
            return None
        try:
            return Credential(sessdata=settings.bilibili_sessdata)
        except Exception as e:
            logger.warning("Failed to create Bilibili credential: {}", e)
            return None

    async def get_user_info(self, uid: str) -> BiliUserInfo:
        """获取用户信息，带重试"""
        try:
            cred = self._create_credential()
            if not cred:
                raise BilibiliAPIError("No credential configured", platform="bilibili")

            u = user.User(uid=int(uid), credential=cred)
            raw = await self._fetch_user_info(u)
            return self._parse_user_info(raw)
        except BilibiliAPIError:
            raise
        except Exception as e:
            if _should_retry(e):
                logger.warning("get_user_info retry: uid={}, error={}", uid, e)
                raise BilibiliAPIError(f"获取用户信息失败: {e}", original_error=e)
            raise BilibiliAPIError(f"获取用户信息失败: {e}", original_error=e)

    @retry(**NO_RETRY_CONFIG)
    async def _fetch_user_info(self, u: user.User) -> dict:
        return await u.get_user_info()

    def _parse_user_info(self, raw: dict) -> BiliUserInfo:
        info = raw.get("info", {})
        detail = raw.get("detail", {})
        stats = raw.get("stat", {})
        return BiliUserInfo(
            mid=raw.get("mid", 0),
            name=info.get("uname", ""),
            sex=info.get("sex"),
            face=info.get("face", ""),
            sign=detail.get("sign"),
            level=info.get("level", 0),
            fans=stats.get("follower", 0),
            attention=info.get("attention", 0),
            archive_count=info.get("archive", {}).get("count"),
            article_count=info.get("article_count", 0),
            following=info.get("following", 0),
            like_num=info.get("like_num", 0),
        )

    async def get_live_status(self, uid: str) -> BiliLiveStatus:
        """获取单个频道的直播状态，带重试"""
        try:
            cred = self._create_credential()
            if not cred:
                return BiliLiveStatus(status="offline")

            backoff = RETRY_MIN
            for attempt in range(MAX_RETRIES):
                try:
                    return await self._fetch_live_status(uid, cred)
                except Exception as e:
                    if _is_rate_limit_error(e):
                        logger.warning(
                            "触发风控 412 uid={}，退避 {}s (attempt {})",
                            uid,
                            backoff,
                            attempt + 1,
                        )
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, RETRY_MAX)
                    else:
                        logger.warning(
                            "获取房间信息失败 uid={} attempt={}: {}",
                            uid,
                            attempt + 1,
                            e,
                        )
                        await asyncio.sleep(1)

            raise BilibiliAPIError(
                f"获取直播状态失败，已重试 {MAX_RETRIES} 次: uid={uid}",
                platform="bilibili",
            )
        except BilibiliAPIError:
            raise
        except Exception as e:
            raise BilibiliAPIError(f"获取直播状态失败: {e}", original_error=e)

    async def _fetch_live_status(self, uid: str, cred: Credential) -> BiliLiveStatus:
        u = user.User(uid=int(uid), credential=cred)
        user_info = await u.get_user_info()

        live_room = user_info.get("live_room")
        if not live_room:
            return BiliLiveStatus(status="offline")

        room_id = live_room.get("room_id", 0)
        if not room_id:
            return BiliLiveStatus(status="offline")

        room = live.LiveRoom(room_id=int(room_id), credential=cred)
        room_info = await room.get_room_info()

        if not room_info:
            return BiliLiveStatus(status="offline")

        live_status = room_info.get("live_status", 0)
        if live_status == 1:
            started_at = None
            live_time = room_info.get("live_time")
            if live_time:
                try:
                    started_at = datetime.fromtimestamp(int(live_time), tz=timezone.utc)
                except (ValueError, OSError, TypeError):
                    pass

            return BiliLiveStatus(
                video_id=str(room_info.get("room_id", "")),
                title=room_info.get("title"),
                thumbnail_url=room_info.get("user_cover") or room_info.get("keyframe"),
                status="live",
                viewer_count=room_info.get("online", 0),
                started_at=started_at,
            )
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

            return BiliLiveStatus(
                video_id=str(room_info.get("room_id", "")),
                title=room_info.get("title"),
                thumbnail_url=room_info.get("user_cover"),
                status="upcoming",
                viewer_count=0,
                scheduled_at=scheduled_at,
            )

        return BiliLiveStatus(status="offline")

    async def batch_get_live_status(
        self, uids: list[str], max_concurrent: int = MAX_CONCURRENT
    ) -> dict[str, BiliLiveStatus]:
        """批量获取多个频道的直播状态"""
        if not uids:
            return {}

        semaphore = asyncio.Semaphore(max_concurrent)
        results: dict[str, BiliLiveStatus] = {}

        async def fetch_with_limit(uid: str) -> tuple[str, BiliLiveStatus]:
            async with semaphore:
                await asyncio.sleep(random.uniform(REQ_SLEEP_MIN, REQ_SLEEP_MAX))
                try:
                    status = await self.get_live_status(uid)
                except BilibiliAPIError:
                    status = BiliLiveStatus(status="offline")
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

    async def get_dynamics(
        self,
        uid: str,
        offset: str = "",
        credential: Optional[Credential] = None,
    ) -> tuple[list[BiliDynamic], str]:
        """获取动态列表，带重试"""
        cred = credential or self._create_credential()
        if not cred:
            return [], ""

        try:
            u = user.User(uid=int(uid), credential=cred)
            raw_result = await u.get_dynamics_new(offset=offset)
            raw_items = raw_result.get("items", [])

            parsed = [self._parse_dynamic(item) for item in raw_items if item]
            return [p for p in parsed if p is not None], raw_result.get("offset", "")
        except Exception as e:
            if _should_retry(e):
                logger.warning("get_dynamics retry: uid={}, error={}", uid, e)
            raise BilibiliAPIError(f"获取动态列表失败: {e}", original_error=e)

    def _parse_dynamic(self, item: dict) -> Optional[BiliDynamic]:
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

            return BiliDynamic(
                dynamic_id=dynamic_id,
                uid=uid,
                uname=uname,
                face=face,
                type=dtype,
                content_nodes=content_nodes,
                images=images,
                repost_content=repost_content,
                timestamp=timestamp,
                url=jump_url,
                topic=topic_name,
                is_top=is_top,
                stat=stat,
            )

        except Exception as e:
            logger.exception(
                "解析新动态项失败: id=%s, error=%s",
                item.get("id_str", "unknown"),
                str(e),
            )
            return None

    @retry(**NO_RETRY_CONFIG)
    async def get_videos(
        self, uid: str, page: int = 1, page_size: int = 30
    ) -> list[BiliVideo]:
        """获取视频列表，带重试"""
        cred = self._create_credential()
        if not cred:
            return []

        try:
            u = user.User(uid=int(uid), credential=cred)
            result = await u.get_videos(pn=page, ps=page_size)
            vlist = result.get("list", {}).get("vlist", [])
            return [self._parse_video(v) for v in vlist]
        except Exception as e:
            if _is_rate_limit_error(e):
                raise BilibiliAPIError(f"获取视频列表失败(风控): {e}", original_error=e)
            raise BilibiliAPIError(f"获取视频列表失败: {e}", original_error=e)

    def _parse_video(self, v: dict) -> BiliVideo:
        return BiliVideo(
            bvid=v.get("bvid", ""),
            title=v.get("title", ""),
            pic=v.get("pic", ""),
            aid=v.get("aid", 0),
            duration=v.get("length", ""),
            pubdate=v.get("created", 0),
            play=v.get("play", 0),
            like=(v.get("stat") or {}).get("like", 0),
            reply=v.get("comment", 0),
        )

    async def get_channel_info(self, uid: str) -> Optional[BiliUserInfo]:
        """获取频道基本信息"""
        cred = self._create_credential()
        if not cred:
            return None

        try:
            u = user.User(uid=int(uid), credential=cred)
            info = await u.get_user_info()
            return self._parse_user_info(info)
        except Exception as e:
            logger.error("Failed to get channel info, uid={}: {}", uid, e)
            return None


@lru_cache
def get_bili_client() -> BiliClient:
    """获取 BiliClient 单例，用于 FastAPI 依赖注入"""
    return BiliClient()


def bili_client_dep(client: BiliClient = Depends(get_bili_client)) -> BiliClient:
    """FastAPI 依赖注入函数"""
    return client
