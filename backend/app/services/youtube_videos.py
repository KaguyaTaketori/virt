import httpx
from app.loguru_config import logger
import math
import subprocess
import json
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from app.config import settings
from app.database import SessionLocal
from app.schemas.schemas import PaginatedVideosResponse, VideoResponse
from app.models.models import Video, Channel
from app.services.youtube_backfill import backfill_channel_videos
from app.database_async import AsyncSessionFactory
from app.services.youtube_sync import sync_channel_videos

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
CACHE_DURATION_MINUTES = 30
LIVE_ARCHIVE_DURATION_THRESHOLD_MINUTES = 30  # 以“视频总时长”为归类依据

def _needs_update(channel: Channel) -> bool:
    if not channel.videos_last_fetched:
        return True
    now = datetime.now(timezone.utc)
    last_fetched = channel.videos_last_fetched
    if last_fetched.tzinfo is None:
        last_fetched = last_fetched.replace(tzinfo=timezone.utc)
    elapsed = now - last_fetched
    return elapsed > timedelta(minutes=CACHE_DURATION_MINUTES)


def _get_videos_from_db(
    db: Session, channel_id: int, page: int, page_size: int, status_filter: str = None
) -> PaginatedVideosResponse:
    query = db.query(Video).filter(Video.channel_id == channel_id)

    if status_filter == "live":
        # 直播 Tab：展示“直播中 / 预约 / 已结束存档”
        # 但 ended 的 archive 在 YouTube 通常会在“很短时间（约半小时）”内归位到 Videos Tab，
        # 但你希望以“视频总时长”作为归类依据：
        # - archive 的 duration_secs <= 30 分钟：更偏向进入 Videos tab（Live tab 不展示）
        # - archive 的 duration_secs >  30 分钟：仍保留在 Live tab（作为长时直播回放归档）
        duration_cutoff_secs = LIVE_ARCHIVE_DURATION_THRESHOLD_MINUTES * 60

        query = query.filter(
            or_(
                Video.status.in_(["live", "upcoming"]),
                and_(
                    Video.status == "archive",
                    Video.live_ended_at.isnot(None),
                    Video.duration_secs.isnot(None),
                    Video.duration_secs > duration_cutoff_secs,
                ),
            )
        )
    elif status_filter == "videos":
        # 视频 Tab：移除 archive，专注展示上传视频（upload）
        query = query.filter(Video.status == "upload")
    elif status_filter == "upload":
        # 仅展示自制上传视频（upload）
        query = query.filter(Video.status == "upload")
    elif status_filter == "short":
        query = query.filter(Video.status == "short")  # Shorts Tab：显示Shorts
    elif status_filter:
        query = query.filter(Video.status == status_filter)
    else:
        query = query.filter(Video.status == "upload")

    query = query.order_by(desc(Video.published_at))

    total = query.count()
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0

    offset = (page - 1) * page_size
    videos = query.offset(offset).limit(page_size).all()

    video_responses = [
        VideoResponse(
            id=v.video_id,
            title=v.title,
            thumbnail_url=v.thumbnail_url,
            duration=v.duration,
            view_count=v.view_count,
            published_at=v.published_at.isoformat() if v.published_at else None,
            status=v.status,
        )
        for v in videos
    ]

    return PaginatedVideosResponse(
        videos=video_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )

async def _refresh_channel_videos(channel: Channel, full_refresh: bool = False) -> None:
    """
    统一的视频刷新入口。
    full_refresh=False → 增量（拉最新 50 条，≈2 配额）
    full_refresh=True  → 全量历史（首次入库时调用）
    """
    if not settings.youtube_api_key:
        return
    async with AsyncSessionFactory() as session:
        ch_obj = await session.get(Channel, channel.id)
        if ch_obj:
            await sync_channel_videos(
                session,
                ch_obj,
                settings.youtube_api_key,
                full_refresh=full_refresh,
            )

async def get_channel_videos(
    channel_id: int,
    page: int = 1,
    page_size: int = 24,
    status_filter: str | None = None,
) -> PaginatedVideosResponse:
    db = SessionLocal()
    try:
        channel = db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return PaginatedVideosResponse(
                videos=[], total=0, page=page, page_size=page_size, total_pages=0
            )

        if _needs_update(channel):
            await _refresh_channel_videos(channel, full_refresh=False)

        return _get_videos_from_db(db, channel_id, page, page_size, status_filter)
    finally:
        db.close()
