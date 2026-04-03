# backend/app/services/youtube_backfill.py
"""
DEPRECATED: 此模块已废弃，请使用 youtube_sync.sync_channel_videos。
将在下一个主版本删除。
"""
from __future__ import annotations
import warnings
warnings.warn(
    "youtube_backfill is deprecated, use youtube_sync.sync_channel_videos",
    DeprecationWarning,
    stacklevel=2,
)




from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.loguru_config import logger
from app.models.models import Video, Channel
from app.services.youtube_utils import (  # ← 统一使用共享工具
    parse_video_item,
)


YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def _convert_to_uploads_playlist(channel_id: str) -> Optional[str]:
    """将普通频道 ID（UCxxx）转换为上传播放列表 ID（UUxxx）。"""
    if channel_id and channel_id.startswith("UC"):
        return "UU" + channel_id[2:]
    return None


async def backfill_channel_videos(
    db: Session,
    channel: Channel,
    full_refresh: bool = False,
) -> int:
    """
    低消耗批量回填频道历史视频。

    参数：
        full_refresh=True  — 拉取全部历史（Initial Backfill）
        full_refresh=False — 仅增量更新最近 50 条

    返回：
        成功处理的视频数量

    配额消耗（每 50 条）：
        PlaylistItems.list × 1 = 1 配额
        Videos.list        × 1 = 1 配额
        合计 ≈ 2 配额 / 50 条
    """
    if not settings.youtube_api_key:
        logger.warning("缺少 YouTube API Key，跳过回填")
        return 0

    uploads_playlist_id = _convert_to_uploads_playlist(channel.channel_id)
    if not uploads_playlist_id:
        logger.warning("无法转换频道 ID: {}", channel.channel_id)
        return 0

    total_processed = 0
    next_page_token: Optional[str] = None

    # 预加载当前已有的 video_id → Video 映射，避免循环内 N+1 查询
    existing_videos_map: dict[str, Video] = {
        v.video_id: v
        for v in db.query(Video).filter(Video.channel_id == channel.id).all()
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            # ── Step 1: PlaylistItems.list 获取视频 ID 列表 ──────────────────
            pl_params = {
                "part":       "snippet",
                "playlistId": uploads_playlist_id,
                "maxResults": 50,
                "key":        settings.youtube_api_key,
            }
            if next_page_token:
                pl_params["pageToken"] = next_page_token

            try:
                pl_resp = await client.get(
                    f"{YOUTUBE_API_BASE}/playlistItems", params=pl_params
                )
                pl_resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error("PlaylistItems.list 失败 {}: {}", e.response.status_code, e.response.text[:200])
                break
            except httpx.RequestError as e:
                logger.error("PlaylistItems.list 网络错误: {}", e)
                break

            pl_data = pl_resp.json()
            items = pl_data.get("items", [])
            if not items:
                break

            video_ids = [
                item["snippet"]["resourceId"]["videoId"]
                for item in items
                if item.get("snippet", {}).get("resourceId", {}).get("videoId")
            ]
            if not video_ids:
                break

            # ── Step 2: Videos.list 批量获取详情 ────────────────────────────
            try:
                vid_resp = await client.get(
                    f"{YOUTUBE_API_BASE}/videos",
                    params={
                        "part": "snippet,contentDetails,statistics,liveStreamingDetails",
                        "id":   ",".join(video_ids),
                        "key":  settings.youtube_api_key,
                    },
                )
                vid_resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error("Videos.list 失败 {}: {}", e.response.status_code, e.response.text[:200])
                # 单批次失败不影响整体，继续下一页
                next_page_token = pl_data.get("nextPageToken")
                if not full_refresh or not next_page_token:
                    break
                continue
            except httpx.RequestError as e:
                logger.error("Videos.list 网络错误: {}", e)
                break

            # ── Step 3: 解析 & Upsert ────────────────────────────────────────
            for item in vid_resp.json().get("items", []):
                vid_id = item["id"]
                # 使用共享工具函数，不再重复解析逻辑
                video_data = parse_video_item(channel.id, channel.platform, item)

                if vid_id in existing_videos_map:
                    existing = existing_videos_map[vid_id]
                    for key in (
                        "title", "thumbnail_url", "duration", "duration_secs",
                        "view_count", "like_count", "status",
                        "published_at", "scheduled_at",
                        "live_started_at", "live_ended_at", "live_chat_id",
                    ):
                        if key in video_data:
                            setattr(existing, key, video_data[key])
                    existing.fetched_at = datetime.now(timezone.utc)
                else:
                    new_video = Video(**{
                        k: v for k, v in video_data.items()
                        if hasattr(Video, k)
                    })
                    new_video.fetched_at = datetime.now(timezone.utc)
                    db.add(new_video)
                    existing_videos_map[vid_id] = new_video

                total_processed += 1

            db.commit()

            # ── Step 4: 翻页控制 ─────────────────────────────────────────────
            next_page_token = pl_data.get("nextPageToken")
            if not full_refresh or not next_page_token:
                break

    channel.videos_last_fetched = datetime.now(timezone.utc)
    db.commit()

    logger.info("频道 {} 回填完成，共处理 {} 个视频", channel.name, total_processed)
    return total_processed