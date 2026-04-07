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
_BATCH_SIZE = 50
_HTTP_TIMEOUT = 20.0


# ── 工具函数 ──────────────────────────────────────────────────────────────────


def _uc_to_uu(channel_id: str) -> Optional[str]:
    if channel_id and channel_id.startswith("UC"):
        return "UU" + channel_id[2:]
    return None


async def _get_real_uploads_playlist_id(
    client: httpx.AsyncClient,
    api_key: str,
    channel_id: str,
) -> Optional[str]:
    params = {
        "key": api_key,
        "part": "contentDetails",
        "id": channel_id,
    }
    try:
        resp = await client.get(
            f"{_YT_API_BASE}/channels",
            params=params,
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if items:
            playlist_id = (
                items[0]
                .get("contentDetails", {})
                .get("relatedPlaylists", {})
                .get("uploads")
            )
            if playlist_id:
                logger.info(
                    "通过 API 成功获取真实 uploads playlist: {} (channel: {})",
                    playlist_id,
                    channel_id,
                )
                return playlist_id
    except Exception as e:
        logger.error(
            "API 获取频道 uploads playlist 失败 channel_id={}: {}", channel_id, e
        )

    return None


async def get_playlist_total_videos(
    client: httpx.AsyncClient,
    api_key: str,
    playlist_id: str,
) -> Optional[int]:
    params = {
        "key": api_key,
        "part": "contentDetails",
        "id": playlist_id,
    }
    try:
        resp = await client.get(
            f"{_YT_API_BASE}/playlists",
            params=params,
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if items:
            return items[0].get("contentDetails", {}).get("itemCount", 0)
    except Exception as e:
        logger.error("API 获取播放列表视频数失败 playlist_id={}: {}", playlist_id, e)
    return None


async def is_channel_full_sync_completed(
    session: AsyncSession,
    channel: Channel,
    api_key: str,
) -> bool:
    async with httpx.AsyncClient() as client:
        playlist_id = _uc_to_uu(channel.channel_id)
        if not playlist_id:
            playlist_id = await _get_real_uploads_playlist_id(
                client, api_key, channel.channel_id
            )

        if not playlist_id:
            return False

        total_videos = await get_playlist_total_videos(client, api_key, playlist_id)
        if total_videos is None:
            return False

        result = await session.execute(
            select(Video).where(Video.channel_id == channel.id)
        )
        db_count = len(result.scalars().all())

        return db_count >= total_videos


async def _get_table_columns(session: AsyncSession, table_name: str) -> set[str]:
    result = await session.execute(text(f"PRAGMA table_info({table_name})"))
    return {row[1] for row in result.fetchall()}


async def _load_existing_video_id_set(
    session: AsyncSession,
    channel_id: int,
) -> set[str]:
    result = await session.execute(
        select(Video.video_id).where(Video.channel_id == channel_id)
    )
    return set(result.scalars().all())


# ── Upsert ────────────────────────────────────────────────────────────────────


from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

async def _upsert_video(
    session: AsyncSession,
    *,
    existing_video_ids: set[str],
    db_video_columns: set[str],
    video_data: dict,
) -> None:
    vid_id: str = video_data["video_id"]
    now = datetime.now(timezone.utc)

    safe_data = {k: v for k, v in video_data.items() if k in db_video_columns}
    if "fetched_at" in db_video_columns:
        safe_data["fetched_at"] = now

    dialect_name = session.bind.dialect.name
    insert_fn = pg_insert if dialect_name == "postgresql" else sqlite_insert

    stmt = insert_fn(Video).values(**safe_data)
    
    update_cols = {
        k: v for k, v in safe_data.items() 
        if k not in ["id", "channel_id", "video_id", "platform"]
    }

    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=["channel_id", "video_id"],
        set_=update_cols
    )

    await session.execute(upsert_stmt)
    
    existing_video_ids.add(vid_id)


# ── YouTube API 调用 ──────────────────────────────────────────────────────────


async def _fetch_playlist_page(
    client: httpx.AsyncClient,
    api_key: str,
    playlist_id: str,
    page_token: Optional[str] = None,
) -> tuple[list[str], Optional[str], Optional[int]]:
    """
    返回: (video_ids, next_page_token, status_code)
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
        if resp.status_code != 200:
            return [], None, resp.status_code

        data = resp.json()
        video_ids = [
            item["snippet"]["resourceId"]["videoId"]
            for item in data.get("items", [])
            if item.get("snippet", {}).get("resourceId", {}).get("kind")
            == "youtube#video"
        ]
        return video_ids, data.get("nextPageToken"), 200
    except Exception as e:
        logger.error("PlaylistItems.list 请求异常: {}", e)
        return [], None, None


async def _fetch_video_details_batch(
    client: httpx.AsyncClient,
    api_key: str,
    video_ids: list[str],
) -> list[dict]:
    if not video_ids:
        return []

    params = {
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
        return resp.json().get("items", [])
    except Exception as e:
        logger.error("Videos.list 获取详情失败: {}", e)
        return []


# ── 公开核心函数 ───────────────────────────────────────────────────────────────


async def sync_channel_videos(
    session: AsyncSession,
    channel: Channel,
    api_key: str,
    *,
    full_refresh: bool = False,
) -> int:
    db_video_columns = await _get_table_columns(session, "videos")
    existing_video_ids = await _load_existing_video_id_set(session, channel.id)

    total_processed = 0
    page_token: Optional[str] = None
    
    playlist_id = _uc_to_uu(channel.channel_id)

    async with httpx.AsyncClient() as client:
        while True:
            video_ids, next_token, status = await _fetch_playlist_page(
                client, api_key, playlist_id, page_token
            )

            if status != 200 and page_token is None:
                logger.warning(
                    "播放列表 ID {} 验证失败(status={})，尝试获取真实 uploads ID...", 
                    playlist_id, status
                )
                playlist_id = await _get_real_uploads_playlist_id(
                    client, api_key, channel.channel_id
                )
                
                if not playlist_id:
                    logger.error("无法获取频道 {} 的任何有效播放列表，同步终止", channel.channel_id)
                    break
                
                video_ids, next_token, status = await _fetch_playlist_page(
                    client, api_key, playlist_id, page_token
                )

            if not video_ids:
                break

            for i in range(0, len(video_ids), _BATCH_SIZE):
                batch_ids = video_ids[i : i + _BATCH_SIZE]
                items = await _fetch_video_details_batch(client, api_key, batch_ids)

                for item in items:
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
        "频道 {!r} 同步任务完成 | 平台: {} | 新增/更新视频数: {} | 模式: {}",
        channel.name,
        channel.platform,
        total_processed,
        "全量" if full_refresh else "仅增量(第一页)",
    )
    return total_processed


async def fetch_and_upsert_single_video(
    session: AsyncSession,
    channel: Channel,
    video_id: str,
    api_key: str,
) -> Optional[dict]:
    async with httpx.AsyncClient() as client:
        items = await _fetch_video_details_batch(client, api_key, [video_id])

    if not items:
        return None

    db_video_columns = await _get_table_columns(session, "videos")
    existing_video_ids = await _load_existing_video_id_set(session, channel.id)
    video_data = parse_video_item(channel.id, channel.platform, items[0])

    await _upsert_video(
        session,
        existing_video_ids=existing_video_ids,
        db_video_columns=db_video_columns,
        video_data=video_data,
    )
    await session.commit()
    return video_data
