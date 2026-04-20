from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session, get_stream_repo
from app.deps.platform_guard import PlatformContext, PlatformGuardDep
from app.models.models import Platform, Stream, StreamStatus
from app.schemas.schemas import StreamResponse
from app.repositories import StreamRepository

router = APIRouter(prefix="/api/streams", tags=["streams"])


@router.get("/live", response_model=list[StreamResponse])
async def get_live_streams(
    platform: Optional[Platform] = None,
    db: AsyncSession = Depends(get_db_session),
    ctx: PlatformContext = PlatformGuardDep,
    stream_repo: StreamRepository = Depends(get_stream_repo),
):
    if platform:
        ctx.assert_platform_access(platform)
        streams = await stream_repo.get_live_streams_with_channel(platform=platform)
    else:
        streams = await stream_repo.get_live_streams_with_channel()
        allowed = ctx.allowed_platforms
        streams = [s for s in streams if s.platform.value in allowed]

    return [_to_response(s) for s in streams]


@router.get("", response_model=list[StreamResponse])
async def get_all_streams(
    platform: Optional[Platform] = None,
    status: Optional[StreamStatus] = None,
    db: AsyncSession = Depends(get_db_session),
    ctx: PlatformContext = PlatformGuardDep,
    stream_repo: StreamRepository = Depends(get_stream_repo),
):
    if platform:
        ctx.assert_platform_access(platform)
        streams = await stream_repo.get_multi_with_channel(
            platform=platform,
            status=status,
        )
    else:
        streams = await stream_repo.get_multi_with_channel(status=status)
        allowed = ctx.allowed_platforms
        streams = [s for s in streams if s.platform.value in allowed]

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
