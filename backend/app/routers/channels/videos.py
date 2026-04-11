from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session
from app.models.models import Channel, Platform, Video
from app.schemas.schemas import PaginatedVideosResponse, VideoResponse
from app.crud.videos import VideoRepository


router = APIRouter()


def parse_status_filter(status: Optional[str]) -> Optional[list[str]]:
    if not status:
        return None
    return [s.strip() for s in status.split(",") if s.strip()]


@router.get("/{channel_id}/videos", response_model=PaginatedVideosResponse)
async def get_channel_videos(
    channel_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.platform == Platform.YOUTUBE:
        return await _get_youtube_videos(db, channel, page, page_size, status)

    if channel.platform == Platform.BILIBILI:
        return await _get_bilibili_videos(db, channel, page, page_size, status)

    return PaginatedVideosResponse(
        videos=[], total=0, page=page, page_size=page_size, total_pages=0
    )


async def _get_youtube_videos(
    db: AsyncSession,
    channel: Channel,
    page: int,
    page_size: int,
    status: Optional[str],
) -> PaginatedVideosResponse:
    video_repo = VideoRepository(db)
    videos, total = await video_repo.get_paginated_by_channel(
        channel.id, page, page_size, status
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return PaginatedVideosResponse(
        videos=[
            VideoResponse(
                id=v.video_id,
                title=v.title or "",
                thumbnail_url=v.thumbnail_url or "",
                duration=v.duration or "",
                view_count=v.view_count or 0,
                published_at=v.published_at.strftime("%Y-%m-%d")
                if v.published_at
                else None,
                status=v.status or "archive",
            )
            for v in videos
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


async def _get_bilibili_videos(
    db: AsyncSession,
    channel: Channel,
    page: int,
    page_size: int,
    status: Optional[str],
) -> PaginatedVideosResponse:
    base_query = select(Video).where(Video.channel_id == channel.id)
    status_list = parse_status_filter(status)
    if status_list:
        if len(status_list) == 1:
            base_query = base_query.where(Video.status == status_list[0])
        else:
            base_query = base_query.where(Video.status.in_(status_list))

    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    paged_query = (
        base_query.order_by(Video.published_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(paged_query)
    videos = result.scalars().all()

    return PaginatedVideosResponse(
        videos=[
            VideoResponse(
                id=v.video_id,
                title=v.title or "",
                thumbnail_url=v.thumbnail_url or "",
                duration=v.duration or "",
                view_count=v.view_count or 0,
                published_at=v.published_at.strftime("%Y-%m-%d")
                if v.published_at
                else None,
                status=v.status or "archive",
            )
            for v in videos
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
