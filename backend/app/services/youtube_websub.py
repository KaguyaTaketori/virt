from __future__ import annotations

import hashlib
import hmac
from app.loguru_config import logger

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database_async import get_async_session, AsyncSessionFactory
from app.models.models import Channel, WebSubSubscription
from app.services.youtube_sync import fetch_and_upsert_single_video
from app.config import settings
from app.deps.guards import validate_websub_callback

# ── 常量 ──────────────────────────────────────────────────────────────────────
_HUB_URL = "https://pubsubhubbub.appspot.com/"
_TOPIC_BASE = "https://www.youtube.com/xml/feeds/videos.xml?channel_id="
_LEASE_DAYS = 9

_YT_API_KEY: str = settings.youtube_api_key
_WEBSUB_SECRET: str = settings.websub_secret

# Atom Feed 命名空间
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}

router = APIRouter(prefix="/api/websub", tags=["websub"])


# ─────────────────────────────────────────────────────────────────────────────
# 订阅发送函数
# ─────────────────────────────────────────────────────────────────────────────
async def subscribe_channel(
    channel_youtube_id: str,
    callback_url: str,
    *,
    mode: str = "subscribe",
    lease_seconds: int = _LEASE_DAYS * 86400,
    secret: str = _WEBSUB_SECRET,
) -> bool:
    topic_url = f"{_TOPIC_BASE}{channel_youtube_id}"

    payload: dict[str, str] = {
        "hub.callback": callback_url,
        "hub.mode": mode,
        "hub.topic": topic_url,
        "hub.lease_seconds": str(lease_seconds),
        "hub.verify": "async",
    }
    if secret:
        payload["hub.secret"] = secret

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(_HUB_URL, data=payload)

        if resp.status_code == 202:
            logger.info(
                f"{mode} 请求已被 Hub 接受 | "
                f"channel={channel_youtube_id} | lease={lease_seconds}s"
            )
            return True
        else:
            logger.warning(
                f"Hub 拒绝 {mode} 请求 | "
                f"channel={channel_youtube_id} | "
                f"status={resp.status_code} | body={resp.text[:200]}"
            )
            return False

    except httpx.RequestError as e:
        logger.error("网络错误，{} 失败: {}", mode, e)
        return False


async def subscribe_all_active_channels(callback_url: str) -> None:
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Channel).where(
                Channel.platform == "youtube",
                Channel.is_active.is_(True),
            )
        )
        channels = result.scalars().all()

    logger.info("开始批量订阅 {} 个频道...", len(channels))
    success_count = 0

    for ch in channels:
        ok = await subscribe_channel(ch.channel_id, callback_url)
        if ok:
            success_count += 1
            async with AsyncSessionFactory() as session:
                sub = await session.scalar(
                    select(WebSubSubscription).where(
                        WebSubSubscription.channel_id == ch.id
                    )
                )
                if not sub:
                    sub = WebSubSubscription(
                        channel_id=ch.id,
                        topic_url=f"{_TOPIC_BASE}{ch.channel_id}",
                        hub_url=_HUB_URL,
                        secret=_WEBSUB_SECRET or None,
                    )
                    session.add(sub)
                sub.subscribed_at = datetime.now(timezone.utc)
                sub.expires_at = datetime.now(timezone.utc) + timedelta(
                    days=_LEASE_DAYS
                )
                await session.commit()
        import asyncio

        await asyncio.sleep(0.3)

    logger.info("批量订阅完成 | 成功 {}/{}", success_count, len(channels))


# ─────────────────────────────────────────────────────────────────────────────
# HMAC 签名验证辅助
# ─────────────────────────────────────────────────────────────────────────────


def _verify_hmac_signature(
    body: bytes, signature_header: Optional[str], secret: str
) -> bool:
    if not secret:
        if not signature_header:
            import logging
            logging.getLogger(__name__).warning(
                "WebSub received push without HMAC signature. "
                "Set WEBSUB_SECRET in production to enforce signature validation."
            )
            return True
        return True

    if not signature_header:
        return False
 
    algo, _, sig_hex = signature_header.partition("=")
    if algo != "sha1":
        return False
 
    expected = hmac.new(secret.encode(), body, hashlib.sha1).hexdigest()
    return hmac.compare_digest(expected, sig_hex)


# ─────────────────────────────────────────────────────────────────────────────
# XML 解析辅助
# ─────────────────────────────────────────────────────────────────────────────


def _parse_atom_feed(xml_body: bytes) -> list[dict]:
    """
    解析 YouTube Hub 推送的 Atom Feed XML，提取 video_id 和 channel_id。

    YouTube 推送示例（简化版）：
        <feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
              xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <yt:videoId>dQw4w9WgXcQ</yt:videoId>
            <yt:channelId>UCuAXFkgsw1L7xaCfnd5JJOw</yt:channelId>
            <title>Never Gonna Give You Up</title>
            <published>2009-10-25T06:57:33+00:00</published>
            ...
          </entry>
        </feed>

    返回：[{"video_id": ..., "channel_id": ..., "title": ...}, ...]
    """
    if not xml_body:
        return []

    try:
        root = ET.fromstring(xml_body)
    except ET.ParseError as e:
        logger.error("XML 解析失败: {} | body={}", e, xml_body[:200])
        return []

    entries = []
    for entry in root.findall("atom:entry", _NS):
        video_id_el = entry.find("yt:videoId", _NS)
        channel_id_el = entry.find("yt:channelId", _NS)
        title_el = entry.find("atom:title", _NS)

        if video_id_el is None or channel_id_el is None:
            continue  # 不完整的 entry，跳过

        entries.append(
            {
                "video_id": video_id_el.text.strip(),
                "channel_id": channel_id_el.text.strip(),
                "title": title_el.text.strip() if title_el is not None else None,
            }
        )

    return entries


# ─────────────────────────────────────────────────────────────────────────────
# 后台任务：拉取视频详情并 Upsert
# ─────────────────────────────────────────────────────────────────────────────


async def _bg_fetch_video(yt_channel_id: str, video_id: str) -> None:
    """
    WebSub 推送触发的后台任务。

    流程：
      1. 用 yt_channel_id 查找数据库中的 Channel 记录
      2. 调用 fetch_and_upsert_single_video 拉取详情并入库
      3. 更新 WebSubSubscription 的推送统计
    """
    if not _YT_API_KEY:
        logger.warning("YOUTUBE_API_KEY 未配置，无法处理 video_id={}", video_id)
        return

    async with AsyncSessionFactory() as session:
        # 查找对应的 Channel 记录
        channel = await session.scalar(
            select(Channel).where(
                Channel.channel_id == yt_channel_id,
                Channel.platform == "youtube",
            )
        )
        if not channel:
            logger.warning("收到未知频道推送 | yt_channel_id={}，跳过", yt_channel_id)
            return

        # 拉取并 Upsert 视频详情
        try:
            video = await fetch_and_upsert_single_video(
                session, channel, video_id, _YT_API_KEY
            )
            if video:
                logger.info(
                    "✓ video_id={} title={} status={}",
                    video_id,
                    video.get("title"),
                    video.get("status"),
                )
        except Exception as e:
            logger.error("✗ 处理 video_id={} 异常: {}", video_id, e)
            return

        # 更新订阅记录的推送统计
        sub = await session.scalar(
            select(WebSubSubscription).where(
                WebSubSubscription.channel_id == channel.id
            )
        )
        if sub:
            sub.last_push_at = datetime.now(timezone.utc)
            sub.push_count = (sub.push_count or 0) + 1
            await session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Router
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/youtube",
    response_class=PlainTextResponse,
    summary="WebSub 订阅验证回调（Hub → 服务端）",
    description=(
        "YouTube PubSubHubbub Hub 在收到订阅请求后，会向此端点发送 GET 请求进行验证。\n"
        "服务端必须原样返回 `hub.challenge` 参数（纯文本），Hub 才会确认订阅生效。"
    ),
)
async def websub_verify(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_topic: str = Query(..., alias="hub.topic"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_lease_seconds: Optional[int] = Query(None, alias="hub.lease_seconds"),
) -> PlainTextResponse:
    if hub_mode not in ("subscribe", "unsubscribe"):
        raise HTTPException(status_code=404, detail="不支持的 hub.mode")
    if not hub_topic.startswith(_TOPIC_BASE):
        raise HTTPException(status_code=404, detail="不认识的 hub.topic")

    yt_channel_id = hub_topic.removeprefix(_TOPIC_BASE)
    logger.info("验证通过 | mode={} | channel={} | lease={}s",
                hub_mode, yt_channel_id, hub_lease_seconds)

    if hub_mode == "subscribe":
        async with AsyncSessionFactory() as session:
            channel = await session.scalar(
                select(Channel).where(
                    Channel.channel_id == yt_channel_id,
                    Channel.platform == "youtube",
                )
            )
            if channel:
                sub = await session.scalar(
                    select(WebSubSubscription).where(
                        WebSubSubscription.channel_id == channel.id
                    )
                )
                if sub:
                    sub.verified = True
                    await session.commit()

    return PlainTextResponse(hub_challenge, status_code=200)


@router.post(
    "/youtube",
    status_code=200,
    summary="接收 YouTube Hub 推送的 Atom Feed",
    description=(
        "YouTube 有新视频/直播时，Hub 向此端点 POST Atom XML Feed。\n"
        "端点必须在 < 200ms 内返回 200，视频详情拉取交由 BackgroundTasks 异步处理，\n"
        "避免 Hub 因超时判定失败而进行重试风暴。"
    ),
)
async def websub_receive(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature: Optional[str] = Header(None, alias="X-Hub-Signature"),
) -> dict:
    """
    接收并处理 YouTube Hub 推送的 Atom XML。

    处理流程（关键：立刻返回 200，不等待视频详情拉取）：
      1. 读取原始 body（bytes，用于 HMAC 验证）
      2. 验证 HMAC 签名（若已配置 WEBSUB_SECRET）
      3. 解析 Atom XML，提取 entry 列表
      4. 为每个 entry 注册 BackgroundTask（异步拉取详情）
      5. 立刻返回 {"ok": True}
    """
    # ── 读取原始 body ──────────────────────────────────────────────────────────
    raw_body: bytes = await request.body()

    # ── HMAC 签名验证（防伪造推送）────────────────────────────────────────────
    if not _verify_hmac_signature(raw_body, x_hub_signature, _WEBSUB_SECRET):
        logger.warning("HMAC 验证失败，拒绝推送 | sig={}", x_hub_signature)
        raise HTTPException(status_code=403, detail="签名验证失败")

    # ── XML 解析 ──────────────────────────────────────────────────────────────
    entries = _parse_atom_feed(raw_body)

    if not entries:
        # 空推送（订阅/退订确认时可能发生）直接返回
        return {"ok": True, "processed": 0}

    # ── 注册后台任务（立刻返回，不阻塞响应）────────────────────────────────────
    count = 0
    for entry in entries:
        video_id = entry["video_id"]
        channel_id = entry["channel_id"]

        logger.info(
            f"收到推送 | channel={channel_id} | "
            f"video_id={video_id!r} | title={entry.get('title')!r}"
        )

        # 将拉取任务加入后台队列，此处不 await，确保立刻返回
        background_tasks.add_task(_bg_fetch_video, channel_id, video_id)
        count += 1

    # ── 立刻 200 OK（Hub 不会重试）────────────────────────────────────────────
    return {"ok": True, "processed": count}


# ─────────────────────────────────────────────────────────────────────────────
# 管理端点（触发订阅 / 续订）
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/youtube/subscribe/{channel_db_id}",
    summary="手动订阅指定频道的 WebSub 推送",
)
async def manual_subscribe(
    channel_db_id: int,
    callback_url: str = Query(
        ...,
        description="本服务的公网回调 URL，如 https://example.com/api/websub/youtube",
    ),
) -> dict:
    """
    对数据库中指定 Channel（通过主键 ID）发起 WebSub 订阅请求。
    适合在后台管理面板手动触发或通过定时任务批量续订。
    """
    allowed_callback = settings.websub_callback_url
    if not allowed_callback or allowed_callback == "https://your-domain.com/api/websub/youtube":
        raise HTTPException(status_code=500, detail="WebSub callback URL not configured")
 
    validated_callback = validate_websub_callback(callback_url, allowed_callback)
 
    async with AsyncSessionFactory() as session:
        channel = await session.get(Channel, channel_db_id)
        if not channel or channel.platform != "youtube":
            raise HTTPException(status_code=404, detail="频道不存在或不是 YouTube 平台")
 
        ok = await subscribe_channel(channel.channel_id, validated_callback)
        if not ok:
            raise HTTPException(status_code=502, detail="Hub 拒绝了订阅请求")
 
        sub = await session.scalar(
            select(WebSubSubscription).where(
                WebSubSubscription.channel_id == channel.id
            )
        )
        if not sub:
            sub = WebSubSubscription(
                channel_id=channel.id,
                topic_url=f"{_TOPIC_BASE}{channel.channel_id}",
                hub_url=_HUB_URL,
                secret=_WEBSUB_SECRET or None,
            )
            session.add(sub)
        sub.subscribed_at = datetime.now(timezone.utc)
        sub.expires_at = datetime.now(timezone.utc) + timedelta(days=_LEASE_DAYS)
        await session.commit()
 
    return {
        "ok": True,
        "channel": channel.name,
        "expires_at": sub.expires_at.isoformat(),
    }


@router.post(
    "/youtube/subscribe-all",
    summary="批量订阅所有激活的 YouTube 频道",
)
async def bulk_subscribe(
    callback_url: str = Query(..., description="本服务的公网回调 URL"),
) -> dict:
    """
    批量订阅数据库中所有 is_active=True 的 YouTube 频道。
    适合在应用首次部署时或每日续订定时任务中调用。
    """
    safe_callback = settings.websub_callback_url
    if not safe_callback or safe_callback == "https://your-domain.com/api/websub/youtube":
        raise HTTPException(status_code=500, detail="WebSub callback URL not configured")
    await subscribe_all_active_channels(safe_callback)
    return {"ok": True, "message": "批量订阅任务已触发，请查看日志了解详情"}


@router.get(
    "/youtube/subscriptions",
    summary="查询所有 WebSub 订阅状态",
)
async def list_subscriptions() -> list[dict]:
    """列出数据库中记录的全部 WebSub 订阅状态，用于运维监控。"""
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(WebSubSubscription, Channel).join(
                Channel, WebSubSubscription.channel_id == Channel.id
            )
        )
        rows = result.all()
 
    now = datetime.now(datetime.timezone.utc)
    return [
        {
            "channel_id": sub.channel_id,
            "channel_name": ch.name,
            "youtube_id": ch.channel_id,
            "verified": sub.verified,
            "subscribed_at": sub.subscribed_at.isoformat() if sub.subscribed_at else None,
            "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
            "is_expired": (sub.expires_at < now) if sub.expires_at else True,
            "last_push_at": sub.last_push_at.isoformat() if sub.last_push_at else None,
            "push_count": sub.push_count,
        }
        for sub, ch in rows
    ]


def _calc_health(sub: WebSubSubscription) -> str:
    """评估订阅健康状态。"""
    if not sub.verified:
        return "未订阅"
    if sub.expires_at and sub.expires_at < datetime.utcnow():
        return "已过期"
    if not sub.last_push_at:
        return "无推送"
    hours_since = (datetime.utcnow() - sub.last_push_at).total_seconds() / 3600
    if hours_since > 48:
        return "异常(48h无推送)"
    return "正常"
