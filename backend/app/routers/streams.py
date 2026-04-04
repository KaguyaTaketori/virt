from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.deps import get_async_db
from app.models.models import Channel, Platform, Stream, StreamStatus, User
from app.schemas.schemas import StreamResponse
from app.auth import get_current_user_optional
from app.services.permissions import has_permission

router = APIRouter(prefix="/api/streams", tags=["streams"])


@router.get("/live", response_model=list[StreamResponse])
async def get_live_streams(
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    has_bilibili_perm = False
    if current_user:
        has_bilibili_perm = await has_permission(
            current_user.id, "bilibili", "access", db
        )

    query = (
        select(Stream)
        .join(Channel, Stream.channel_id == Channel.id)
        .where(Stream.status == StreamStatus.LIVE)
    )

    if not has_bilibili_perm:
        query = query.where(Channel.platform == Platform.YOUTUBE)

    result = await db.execute(query)
    streams = result.scalars().all()
    return [_to_response(s) for s in streams]


@router.get("", response_model=list[StreamResponse])
async def get_all_streams(
    platform: Optional[Platform] = None,
    status: Optional[StreamStatus] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    has_bilibili_perm = False
    if current_user:
        has_bilibili_perm = await has_permission(
            current_user.id, "bilibili", "access", db
        )

    query = select(Stream).join(Channel, Stream.channel_id == Channel.id)

    if not has_bilibili_perm:
        query = query.where(Channel.platform == Platform.YOUTUBE)

    if platform is not None:
        query = query.where(Stream.platform == platform)
    if status is not None:
        query = query.where(Stream.status == status)

    result = await db.execute(query)
    streams = result.scalars().all()
    return [_to_response(s) for s in streams]


def _to_response(stream: Stream) -> StreamResponse:
    ch = stream.channel
    return StreamResponse(
        id=stream.id,
        channel_id=stream.channel_id,
        platform=stream.platform,
        video_id=stream.video_id,
        title=stream.title,
        thumbnail_url=stream.thumbnail_url,
        viewer_count=stream.viewer_count,
        status=stream.status,
        started_at=stream.started_at,
        scheduled_at=stream.scheduled_at,
        channel_name=ch.name if ch else None,
        channel_avatar=ch.avatar_url if ch else None,
        channel_avatar_shape=ch.avatar_shape if ch else None,
        org_id=ch.org_id if ch else None,
    )
