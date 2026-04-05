import math
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, and_, or_, select, func

from app.config import settings
from app.database_async import AsyncSessionFactory
from app.schemas.schemas import PaginatedVideosResponse, VideoResponse
from app.models.models import Video, Channel
from app.services.youtube_sync import sync_channel_videos
from app.services.api_key_manager import get_api_key, is_api_available

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


async def _get_videos_from_db(
    db: AsyncSession,
    channel_id: int,
    page: int,
    page_size: int,
    status_filter: str = None,
) -> PaginatedVideosResponse:
    query = select(Video).where(Video.channel_id == channel_id)

    if status_filter == "live":
        duration_cutoff_secs = LIVE_ARCHIVE_DURATION_THRESHOLD_MINUTES * 60

        query = query.where(
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
        query = query.where(Video.status == "upload")
    elif status_filter == "upload":
        query = query.where(Video.status == "upload")
    elif status_filter == "short":
        query = query.where(Video.status == "short")
    elif status_filter:
        query = query.where(Video.status == status_filter)
    else:
        query = query.where(Video.status == "upload")

    query = query.order_by(desc(Video.published_at))

    result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = result.scalar() or 0
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    videos = result.scalars().all()

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
    if not await is_api_available():
        return
    api_key = await get_api_key()
    async with AsyncSessionFactory() as session:
        ch_obj = await session.get(Channel, channel.id)
        if ch_obj:
            await sync_channel_videos(
                session,
                ch_obj,
                api_key,
                full_refresh=full_refresh,
            )


async def get_channel_videos(
    channel_id: int,
    page: int = 1,
    page_size: int = 24,
    status_filter: str | None = None,
) -> PaginatedVideosResponse:
    async with AsyncSessionFactory() as db:
        result = await db.execute(select(Channel).where(Channel.id == channel_id))
        channel = result.scalar_one_or_none()
        if not channel:
            return PaginatedVideosResponse(
                videos=[], total=0, page=page, page_size=page_size, total_pages=0
            )

        if _needs_update(channel):
            await _refresh_channel_videos(channel, full_refresh=False)

        return await _get_videos_from_db(db, channel_id, page, page_size, status_filter)
