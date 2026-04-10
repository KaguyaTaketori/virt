import math
from datetime import datetime, timezone, timedelta
from sqlalchemy import desc, and_, or_, select, func

from app.schemas.schemas import PaginatedVideosResponse, VideoResponse
from app.models.models import Video, Channel
from app.services.youtube_sync import sync_channel_videos
from app.services.api_key_manager import get_api_key, is_api_available
from app.crud.session import session_scope
from app.crud import ChannelRepository, VideoRepository

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
CACHE_DURATION_MINUTES = 30
LIVE_ARCHIVE_DURATION_THRESHOLD_MINUTES = 30


def _needs_update(channel: Channel) -> bool:
    if not channel.videos_last_fetched:
        return True
    now = datetime.now(timezone.utc)
    last_fetched = channel.videos_last_fetched
    if last_fetched.tzinfo is None:
        last_fetched = last_fetched.replace(tzinfo=timezone.utc)
    elapsed = now - last_fetched
    return elapsed > timedelta(minutes=CACHE_DURATION_MINUTES)


async def get_channel_videos(
    channel_id: int,
    page: int = 1,
    page_size: int = 24,
    status_filter: str | None = None,
) -> PaginatedVideosResponse:
    async with session_scope() as session:
        channel_repo = ChannelRepository(session)
        channel = await channel_repo.get(channel_id)

        if not channel:
            return PaginatedVideosResponse(
                videos=[], total=0, page=page, page_size=page_size, total_pages=0
            )

        if _needs_update(channel):
            await _refresh_channel_videos(channel, full_refresh=False)

        return await _get_videos_from_session(
            session, channel_id, page, page_size, status_filter
        )


async def _refresh_channel_videos(channel: Channel, full_refresh: bool = False) -> None:
    if not await is_api_available():
        return
    api_key = await get_api_key()

    async with session_scope() as session:
        channel_repo = ChannelRepository(session)
        ch_obj = await channel_repo.get(channel.id)
        if ch_obj:
            await sync_channel_videos(
                session, ch_obj, api_key, full_refresh=full_refresh
            )


async def _get_videos_from_session(
    session,
    channel_id: int,
    page: int,
    page_size: int,
    status_filter: str | None = None,
) -> PaginatedVideosResponse:
    video_repo = VideoRepository(session)
    videos, total = await video_repo.get_paginated_by_channel(
        channel_id,
        page=page,
        page_size=page_size,
        status=status_filter,
    )

    total_pages = math.ceil(total / page_size) if page_size > 0 else 0

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


# Legacy exports for backward compatibility
from app.crud.session import session_scope as _session_scope

__all__ = [
    "get_channel_videos",
    "YOUTUBE_API_BASE",
    "CACHE_DURATION_MINUTES",
    "LIVE_ARCHIVE_DURATION_THRESHOLD_MINUTES",
]
