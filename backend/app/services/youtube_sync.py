"""
youtube_sync.py
───────────────
YouTube 视频元数据低消耗同步模块。

核心策略：
  1. 将频道 ID UCxxx → 上传播放列表 UUxxx
     用 PlaylistItems.list 拉取视频 ID 列表（每50条消耗 1 配额，而非 Search.list 的 100）
  2. 用 Videos.list 批量（每次最多50个）拉取视频详情（每50条消耗 1 配额）
  3. Upsert 完全在 Python 层完成，兼容 SQLite 和 PostgreSQL

对外暴露的核心函数：
  - sync_channel_videos(session, channel, full_refresh)  — 频道级全量/增量同步
  - fetch_and_upsert_single_video(session, channel, video_id) — WebSub 推送后单条更新
"""

from __future__ import annotations

import asyncio
from app.loggeruru_config import loggerger
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Channel, Video
from enum import Enum


class VideoStatusEnum(str, Enum):
    LIVE = "live"
    UPCOMING = "upcoming"
    ARCHIVE = "archive"
    UPLOAD = "upload"
    SHORT = "short"


# ── 常量 ──────────────────────────────────────────────────────────────────────
_YT_API_BASE = "https://www.googleapis.com/youtube/v3"
_BATCH_SIZE = 50  # Videos.list / PlaylistItems.list 每次最多 50 条
_HTTP_TIMEOUT = 20.0  # 秒


# ─────────────────────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────────────────────


def _uc_to_uu(channel_id: str) -> Optional[str]:
    """
    将 YouTube 频道 ID（UCxxx）转换为上传播放列表 ID（UUxxx）。
    这是零额外配额消耗拉取全部视频的核心技巧：
      - Search.list (channelId=UCxxx) → 100 配额/次，最多返回 500 条
      - PlaylistItems.list (UUxxx)    →   1 配额/次，无上限翻页
    """
    if channel_id and channel_id.startswith("UC"):
        return "UU" + channel_id[2:]
    return None


def _parse_dt(iso_str: Optional[str]) -> Optional[datetime]:
    """
    把 YouTube 返回的 ISO 8601 字符串（带 'Z' 或 '+00:00'）转为 aware datetime（UTC）。
    Python 3.10 以下 fromisoformat 不识别 'Z'，需手动替换。
    """
    if not iso_str:
        return None
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _parse_duration(iso_duration: Optional[str]) -> tuple[Optional[str], int]:
    """
    解析 ISO 8601 时长字符串（如 'PT1H23M45S'）。
    返回 (格式化字符串, 总秒数)。
    格式化字符串示例：'1:23:45'、'23:45'、'0:45'。
    """
    if not iso_duration:
        return None, 0

    match = re.fullmatch(
        r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        iso_duration,
    )
    if not match:
        return None, 0

    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0) + days * 24
    minutes = int(match.group(3) or 0)
    seconds = int(match.group(4) or 0)

    total_secs = hours * 3600 + minutes * 60 + seconds

    if hours > 0:
        fmt = f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        fmt = f"{minutes}:{seconds:02d}"

    return fmt, total_secs


def _determine_status(item: dict, total_secs: int) -> VideoStatusEnum:
    """
    根据 Videos.list 返回的字段精准判定视频状态：

    判定优先级：
      1. 有 liveStreamingDetails → 直播相关
         - actualEndTime 存在   → archive（直播已结束）
         - actualStartTime 存在  → live（正在直播）
         - scheduledStartTime 存在 → upcoming（待机室）
      2. 无 liveStreamingDetails，时长 ≤ 61 秒 → short（Shorts）
      3. 其余 → upload（普通视频）
    """
    live_details: dict = item.get("liveStreamingDetails") or {}

    if live_details:
        if live_details.get("actualEndTime"):
            return VideoStatusEnum.ARCHIVE
        if live_details.get("actualStartTime"):
            return VideoStatusEnum.LIVE
        if live_details.get("scheduledStartTime"):
            return VideoStatusEnum.UPCOMING

    # Shorts 判定：时长 ≤ 61 秒（留 1 秒余量避免临界值误判）
    if 0 < total_secs <= 61:
        return VideoStatusEnum.SHORT

    return VideoStatusEnum.UPLOAD


def _extract_thumbnail(snippet: dict) -> Optional[str]:
    """按质量优先级提取封面 URL。"""
    thumbs = snippet.get("thumbnails", {})
    for quality in ("maxres", "standard", "high", "medium", "default"):
        url = thumbs.get(quality, {}).get("url")
        if url:
            return url
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 通用 Upsert 辅助（Python 层，跨库兼容）
# ─────────────────────────────────────────────────────────────────────────────


async def _load_existing_video_map(
    session: AsyncSession, channel_id: int
) -> dict[str, Video]:
    """
    一次性加载该频道所有已有的 Video 对象，构建 video_id → Video 的映射表。

    设计原因：
      避免在循环中对每个 video_id 单独 SELECT，减少 N+1 查询。
      此映射表在同一次 sync 调用内共享，内存开销极小（~几千条记录）。
    """
    result = await session.execute(select(Video).where(Video.channel_id == channel_id))
    return {v.video_id: v for v in result.scalars().all()}


async def _get_table_columns(session: AsyncSession, table_name: str) -> set[str]:
    """读取数据库真实存在的列名（避免模型/库 schema 漂移导致 SQL 报错）。"""
    result = await session.execute(text(f"PRAGMA table_info({table_name})"))
    # PRAGMA table_info: cid, name, type, notnull, dflt_value, pk
    return {row[1] for row in result.fetchall()}


async def _load_existing_video_id_set(
    session: AsyncSession,
    channel_id: int,
) -> set[str]:
    """只加载 video_id，避免一次 SELECT 整个 Video mapping。"""
    result = await session.execute(
        select(Video.video_id).where(Video.channel_id == channel_id)
    )
    return set(result.scalars().all())


async def _upsert_video(
    session: AsyncSession,
    *,
    existing_video_ids: set[str],
    db_video_columns: set[str],
    channel: Channel,
    video_data: dict,
) -> None:
    """
    Python 层 Upsert（不依赖 ON CONFLICT）：
    - 先判断 DB 中是否已有该 video_id（仅靠 video_id 现有列）
    - update/insert 时只写入 DB 实际存在的列，避免 `no such column`。
    """
    vid_id: str = video_data["video_id"]
    now = datetime.now(timezone.utc)

    # 过滤到“数据库里真实存在”的列
    filtered_video_data = {k: v for k, v in video_data.items() if k in db_video_columns}

    # fetched_at 在现有表里通常存在；若不存在则不写
    if "fetched_at" in db_video_columns:
        filtered_video_data["fetched_at"] = now

    if vid_id in existing_video_ids:
        if filtered_video_data:
            await session.execute(
                update(Video)
                .where(Video.channel_id == channel.id, Video.video_id == vid_id)
                .values(**filtered_video_data)
            )
        return

    # INSERT：只写入 DB 实际存在列
    values = {
        "channel_id": channel.id,
        "platform": channel.platform,
        "video_id": vid_id,
    }
    values = {k: v for k, v in values.items() if k in db_video_columns}
    for k, v in filtered_video_data.items():
        if k in db_video_columns:
            values[k] = v

    await session.execute(insert(Video).values(**values))
    existing_video_ids.add(vid_id)


# ─────────────────────────────────────────────────────────────────────────────
# YouTube API 调用层
# ─────────────────────────────────────────────────────────────────────────────


async def _fetch_playlist_page(
    client: httpx.AsyncClient,
    api_key: str,
    playlist_id: str,
    page_token: Optional[str] = None,
) -> tuple[list[str], Optional[str]]:
    """
    调用 PlaylistItems.list 获取一页（最多50条）视频 ID。
    返回 (video_id 列表, 下一页 token)。
    消耗：1 配额/次。
    """
    params: dict = {
        "key": api_key,
        "part": "snippet",
        "playlistId": playlist_id,
        "maxResults": _BATCH_SIZE,
    }
    if page_token:
        params["pageToken"] = page_token

    try:
        resp = await client.get(
            f"{_YT_API_BASE}/playlistItems",
            params=params,
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(
            f"PlaylistItems.list HTTP error {e.response.status_code}: {e.response.text[:200]}"
        )
        return [], None
    except httpx.RequestError as e:
        logger.error("PlaylistItems.list network error: {}", e)
        return [], None

    data = resp.json()
    video_ids: list[str] = [
        item["snippet"]["resourceId"]["videoId"]
        for item in data.get("items", [])
        if item.get("snippet", {}).get("resourceId", {}).get("kind") == "youtube#video"
    ]
    next_token: Optional[str] = data.get("nextPageToken")
    return video_ids, next_token


async def _fetch_video_details_batch(
    client: httpx.AsyncClient,
    api_key: str,
    video_ids: list[str],
) -> list[dict]:
    """
    批量调用 Videos.list 拉取最多50个视频的完整详情。
    一次调用包含：snippet + contentDetails + statistics + liveStreamingDetails。
    消耗：1 配额/次（无论返回多少条，最多50条算1次）。
    """
    if not video_ids:
        return []

    params: dict = {
        "key": api_key,
        "part": "snippet,contentDetails,statistics,liveStreamingDetails",
        "id": ",".join(video_ids),
    }

    try:
        resp = await client.get(
            f"{_YT_API_BASE}/videos",
            params=params,
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(
            f"Videos.list HTTP error {e.response.status_code}: {e.response.text[:200]}"
        )
        return []
    except httpx.RequestError as e:
        logger.error("Videos.list network error: {}", e)
        return []

    return resp.json().get("items", [])


def _parse_video_item(channel: Channel, item: dict) -> dict:
    """
    将 YouTube API 的 video item dict 解析为可直接用于 Upsert 的字段字典。
    """
    video_id: str = item["id"]
    snippet: dict = item.get("snippet", {})
    content: dict = item.get("contentDetails", {})
    stats: dict = item.get("statistics", {})
    live: dict = item.get("liveStreamingDetails") or {}

    duration_fmt, total_secs = _parse_duration(content.get("duration"))
    status = _determine_status(item, total_secs)

    return {
        "video_id": video_id,
        "title": snippet.get("title"),
        "thumbnail_url": _extract_thumbnail(snippet),
        "duration": duration_fmt,
        "duration_secs": total_secs if total_secs > 0 else None,
        "view_count": int(stats.get("viewCount", 0)),
        "like_count": int(stats["likeCount"]) if stats.get("likeCount") else None,
        "status": status.value,
        "published_at": _parse_dt(snippet.get("publishedAt")),
        "scheduled_at": _parse_dt(live.get("scheduledStartTime")),
        "live_started_at": _parse_dt(live.get("actualStartTime")),
        "live_ended_at": _parse_dt(live.get("actualEndTime")),
        "live_chat_id": live.get("activeLiveChatId"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 公开核心函数：频道级同步
# ─────────────────────────────────────────────────────────────────────────────


async def sync_channel_videos(
    session: AsyncSession,
    channel: Channel,
    api_key: str,
    *,
    full_refresh: bool = False,
) -> int:
    """
    同步指定频道的视频列表到数据库。

    参数：
        session       — 异步 SQLAlchemy Session
        channel       — Channel ORM 对象
        api_key       — YouTube Data API v3 密钥
        full_refresh  — True: 翻页拉取全量历史（首次收录）
                        False: 仅拉取第一页50条（每日兜底对账）

    返回：
        本次处理的视频条数。

    配额估算（full_refresh=False）：
        PlaylistItems.list × 1  = 1 配额
        Videos.list × 1         = 1 配额
        合计 ≈ 2 配额/频道/次

    配额估算（full_refresh=True，以100个视频为例）：
        PlaylistItems.list × 2  = 2 配额
        Videos.list × 2         = 2 配额
        合计 ≈ 4 配额/100视频
    """
    playlist_id = _uc_to_uu(channel.channel_id)
    if not playlist_id:
        logger.warning(
            f"Cannot convert channel_id={channel.channel_id} to playlist_id, skipping"
        )
        return 0

    # 只预加载 video_id（避免一次 SELECT Video 全列导致缺列报错）
    db_video_columns = await _get_table_columns(session, "videos")
    existing_video_ids = await _load_existing_video_id_set(session, channel.id)

    total_processed = 0
    page_token: Optional[str] = None

    async with httpx.AsyncClient() as client:
        while True:
            # ── Step 1: 获取一页视频 ID 列表（1 配额）────────────────────────
            video_ids, next_token = await _fetch_playlist_page(
                client, api_key, playlist_id, page_token
            )
            if not video_ids:
                break

            # ── Step 2: 分批（每次≤50）拉取视频详情（每批 1 配额）──────────
            for i in range(0, len(video_ids), _BATCH_SIZE):
                batch = video_ids[i : i + _BATCH_SIZE]
                items = await _fetch_video_details_batch(client, api_key, batch)

                for item in items:
                    video_data = _parse_video_item(channel, item)
                    await _upsert_video(
                        session,
                        existing_video_ids=existing_video_ids,
                        db_video_columns=db_video_columns,
                        channel=channel,
                        video_data=video_data,
                    )
                    total_processed += 1

                # 每批提交一次，控制事务大小
                await session.flush()

            # ── Step 3: 翻页控制 ─────────────────────────────────────────────
            if not full_refresh or not next_token:
                break  # 增量模式只取第一页；全量模式翻页到底
            page_token = next_token

    # 更新频道的最后拉取时间戳
    channel.videos_last_fetched = datetime.now(timezone.utc)
    await session.commit()

    logger.info(
        f"Channel {channel.name!r} sync complete | "
        f"full_refresh={full_refresh} | processed={total_processed}"
    )
    return total_processed


# ─────────────────────────────────────────────────────────────────────────────
# 公开核心函数：单条视频更新（供 WebSub 后台任务调用）
# ─────────────────────────────────────────────────────────────────────────────


async def fetch_and_upsert_single_video(
    session: AsyncSession,
    channel: Channel,
    video_id: str,
    api_key: str,
) -> Optional[dict]:
    """
    拉取单个视频的最新详情并 Upsert 到数据库。
    专门为 WebSub 推送触发的后台任务设计，做到"零延迟写入"。

    消耗：Videos.list × 1 = 1 配额。
    """
    async with httpx.AsyncClient() as client:
        items = await _fetch_video_details_batch(client, api_key, [video_id])

    if not items:
        logger.warning("Single update: video_id={} no data, skipping", video_id)
        return None

    video_data = _parse_video_item(channel, items[0])
    db_video_columns = await _get_table_columns(session, "videos")
    existing_video_ids = await _load_existing_video_id_set(session, channel.id)
    await _upsert_video(
        session,
        existing_video_ids=existing_video_ids,
        db_video_columns=db_video_columns,
        channel=channel,
        video_data=video_data,
    )

    await session.commit()
    logger.info(
        f"Single upsert complete | video_id={video_id!r} "
        f"title={video_data.get('title')!r} status={video_data.get('status')}"
    )
    return video_data
