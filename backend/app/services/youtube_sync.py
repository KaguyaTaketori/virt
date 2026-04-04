from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.loguru_config import logger
from app.models.models import Channel, Video
from app.services.youtube_utils import parse_video_item

_YT_API_BASE = "https://www.googleapis.com/youtube/v3"
_BATCH_SIZE  = 50
_HTTP_TIMEOUT = 20.0


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _uc_to_uu(channel_id: str) -> Optional[str]:
    """将频道 ID（UCxxx）转为上传播放列表 ID（UUxxx）。"""
    if channel_id and channel_id.startswith("UC"):
        return "UU" + channel_id[2:]
    return None

async def _get_real_uploads_playlist_id(client: httpx.AsyncClient, api_key: str, channel_id: str) -> Optional[str]:
    params = {
        "key": api_key,
        "part": "contentDetails",
        "id": channel_id,
    }
    try:
        resp = await client.get(f"{_YT_API_BASE}/channels", params=params)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if items:
            return items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    except Exception as e:
        logger.error("获取频道详情失败: {}", e)
    return None


async def _get_table_columns(session: AsyncSession, table_name: str) -> set[str]:
    """读取数据库真实存在的列名，避免 schema 漂移导致 SQL 报错。"""
    result = await session.execute(text(f"PRAGMA table_info({table_name})"))
    return {row[1] for row in result.fetchall()}


async def _load_existing_video_id_set(
    session: AsyncSession,
    channel_id: int,
) -> set[str]:
    """只加载 video_id 集合，避免 SELECT 整个 Video 对象造成内存浪费。"""
    result = await session.execute(
        select(Video.video_id).where(Video.channel_id == channel_id)
    )
    return set(result.scalars().all())


# ── Upsert ────────────────────────────────────────────────────────────────────

async def _upsert_video(
    session: AsyncSession,
    *,
    existing_video_ids: set[str],
    db_video_columns: set[str],
    video_data: dict,
) -> None:
    """
    Python 层 Upsert（不依赖 ON CONFLICT，跨库兼容）。
    只写入数据库实际存在的列，防止 schema 漂移导致 'no such column'。
    """
    vid_id: str = video_data["video_id"]
    now = datetime.now(timezone.utc)

    # 过滤到 DB 真实存在的列
    safe_data = {k: v for k, v in video_data.items() if k in db_video_columns}
    if "fetched_at" in db_video_columns:
        safe_data["fetched_at"] = now

    if vid_id in existing_video_ids:
        # UPDATE：只更新安全字段
        safe_data.pop("channel_id", None)
        safe_data.pop("platform", None)
        safe_data.pop("video_id", None)
        if safe_data:
            await session.execute(
                update(Video)
                .where(
                    Video.channel_id == video_data["channel_id"],
                    Video.video_id == vid_id,
                )
                .values(**safe_data)
            )
        return

    # INSERT
    values = {k: v for k, v in safe_data.items() if k in db_video_columns}
    await session.execute(insert(Video).values(**values))
    existing_video_ids.add(vid_id)


# ── YouTube API 调用 ──────────────────────────────────────────────────────────

async def _fetch_playlist_page(
    client: httpx.AsyncClient,
    api_key: str,
    playlist_id: str,
    page_token: Optional[str] = None,
) -> tuple[list[str], Optional[str]]:
    """
    PlaylistItems.list 获取一页视频 ID。
    消耗：1 配额 / 次（最多 50 条）。
    """
    params: dict = {
        "key":        api_key,
        "part":       "snippet",
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
        logger.error("Failed ID: {}", playlist_id)
        return [], None
    except httpx.RequestError as e:
        logger.error("PlaylistItems.list 网络错误: {}", e)
        return [], None

    data = resp.json()
    video_ids = [
        item["snippet"]["resourceId"]["videoId"]
        for item in data.get("items", [])
        if item.get("snippet", {}).get("resourceId", {}).get("kind") == "youtube#video"
    ]
    return video_ids, data.get("nextPageToken")


async def _fetch_video_details_batch(
    client: httpx.AsyncClient,
    api_key: str,
    video_ids: list[str],
) -> list[dict]:
    """
    Videos.list 批量拉取视频详情（最多 50 条）。
    消耗：1 配额 / 次。
    """
    if not video_ids:
        return []

    params = {
        "key":  api_key,
        "part": "snippet,contentDetails,statistics,liveStreamingDetails",
        "id":   ",".join(video_ids),
    }
    try:
        resp = await client.get(
            f"{_YT_API_BASE}/videos",
            params=params,
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error("Videos.list HTTP {}: {}", e.response.status_code, e.response.text[:200])
        return []
    except httpx.RequestError as e:
        logger.error("Videos.list 网络错误: {}", e)
        return []

    return resp.json().get("items", [])


# ── 公开核心函数 ───────────────────────────────────────────────────────────────

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
        full_refresh=False — 仅拉取第 1 页 50 条（每日增量兜底，≈2 配额/频道）
        full_refresh=True  — 翻页拉取全量历史（首次收录，≈N/50×2 配额）
    """
    playlist_id = _uc_to_uu(channel.channel_id)
    if not playlist_id:
        logger.warning("无法转换 channel_id={} 为播放列表 ID", channel.channel_id)
        return 0

    db_video_columns   = await _get_table_columns(session, "videos")
    existing_video_ids = await _load_existing_video_id_set(session, channel.id)

    total_processed = 0
    page_token: Optional[str] = None

    async with httpx.AsyncClient() as client:
        while True:
            video_ids, next_token = await _fetch_playlist_page(
                client, api_key, playlist_id, page_token
            )
            if not video_ids:
                break

            for i in range(0, len(video_ids), _BATCH_SIZE):
                batch = video_ids[i : i + _BATCH_SIZE]
                items = await _fetch_video_details_batch(client, api_key, batch)

                for item in items:
                    # 使用共享工具函数解析，不再重复实现
                    video_data = parse_video_item(channel.id, channel.platform, item)
                    await _upsert_video(
                        session,
                        existing_video_ids=existing_video_ids,
                        db_video_columns=db_video_columns,
                        video_data=video_data,
                    )
                    total_processed += 1

                await session.flush()

            if not full_refresh or not next_token:
                break
            page_token = next_token

    channel.videos_last_fetched = datetime.now(timezone.utc)
    await session.commit()

    logger.info(
        "Channel {!r} 同步完成 | full_refresh={} | processed={}",
        channel.name, full_refresh, total_processed,
    )
    return total_processed


async def fetch_and_upsert_single_video(
    session: AsyncSession,
    channel: Channel,
    video_id: str,
    api_key: str,
) -> Optional[dict]:
    """
    拉取单个视频最新详情并 Upsert（供 WebSub 后台任务调用）。
    消耗：Videos.list × 1 = 1 配额。
    """
    async with httpx.AsyncClient() as client:
        items = await _fetch_video_details_batch(client, api_key, [video_id])

    if not items:
        logger.warning("Single update: video_id={} 无数据，跳过", video_id)
        return None

    db_video_columns   = await _get_table_columns(session, "videos")
    existing_video_ids = await _load_existing_video_id_set(session, channel.id)
    video_data = parse_video_item(channel.id, channel.platform, items[0])

    await _upsert_video(
        session,
        existing_video_ids=existing_video_ids,
        db_video_columns=db_video_columns,
        video_data=video_data,
    )
    await session.commit()

    logger.info(
        "Single upsert 完成 | video_id={!r} title={!r} status={}",
        video_id, video_data.get("title"), video_data.get("status"),
    )
    return video_data