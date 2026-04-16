from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session, get_channel_repo, get_video_repo
from app.models.models import Platform
from app.schemas.schemas import PaginatedVideosResponse, VideoResponse
from app.repositories import ChannelRepository, VideoRepository


router = APIRouter()


@router.get("/{channel_id}/videos", response_model=PaginatedVideosResponse)
async def get_channel_videos(
    channel_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session),
    channel_repo: ChannelRepository = Depends(get_channel_repo),
    video_repo: VideoRepository = Depends(get_video_repo),
):
    channel = await channel_repo.get(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.platform == Platform.YOUTUBE:
        return await _get_youtube_videos(video_repo, channel, page, page_size, status)

    if channel.platform == Platform.BILIBILI:
        return await _get_bilibili_videos(video_repo, channel, page, page_size, status)

    return PaginatedVideosResponse(
        videos=[], total=0, page=page, page_size=page_size, total_pages=0
    )


async def _get_youtube_videos(
    video_repo: VideoRepository,
    channel,
    page: int,
    page_size: int,
    status: Optional[str],
) -> PaginatedVideosResponse:
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
    video_repo: VideoRepository,
    channel,
    page: int,
    page_size: int,
    status: Optional[str],
) -> PaginatedVideosResponse:
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
