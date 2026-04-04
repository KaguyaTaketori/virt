from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_async_db
from app.models.models import Channel, Platform, Video
from app.schemas.schemas import PaginatedVideosResponse, VideoResponse
from app.services.youtube_videos import get_channel_videos as fetch_yt_videos
from app.services.bilibili_fetcher import sync_bilibili_channel_videos

router = APIRouter()


@router.get("/{channel_id}/videos", response_model=PaginatedVideosResponse)
async def get_channel_videos(
    channel_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.platform == Platform.YOUTUBE:
        return await fetch_yt_videos(channel.id, page, page_size, status)

    if channel.platform == Platform.BILIBILI:
        return await _get_bilibili_videos(db, channel, page, page_size, status)

    return PaginatedVideosResponse(
        videos=[], total=0, page=page, page_size=page_size, total_pages=0
    )


async def _get_bilibili_videos(
    db: AsyncSession,
    channel: Channel,
    page: int,
    page_size: int,
    status: Optional[str],
) -> PaginatedVideosResponse:
    count_result = await db.execute(
        select(Video).where(Video.channel_id == channel.id)
    )
    if not count_result.scalars().all():
        await sync_bilibili_channel_videos(db, channel.id, channel.channel_id)

    query = select(Video).where(Video.channel_id == channel.id)
    if status:
        query = query.where(Video.status == status)

    total_result = await db.execute(query)
    total = len(total_result.scalars().all())
    total_pages = (total + page_size - 1) // page_size if total else 0

    query = query.order_by(Video.published_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    videos = result.scalars().all()

    return PaginatedVideosResponse(
        videos=[
            VideoResponse(
                id=v.video_id,
                title=v.title or "",
                thumbnail_url=v.thumbnail_url or "",
                duration=v.duration or "",
                view_count=v.view_count or 0,
                published_at=v.published_at.strftime("%Y-%m-%d") if v.published_at else None,
                status=v.status or "archive",
            )
            for v in videos
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )