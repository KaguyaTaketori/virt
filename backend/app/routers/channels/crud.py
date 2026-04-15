from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.loguru_config import logger
from app.database import session_scope
from app.deps import get_db_session
from app.deps.guards import AdminUser
from app.deps.platform_guard import PlatformContext, PlatformGuardDep
from app.models.models import (
    Channel,
    Platform,
    User,
    UserChannel,
)
from app.schemas.schemas import ChannelCreate, ChannelResponse, ChannelUpdate
from app.integrations.youtube import get_youtube_sync_service
from app.services.api_key_manager import get_api_key, is_api_available
from app.constants import UserChannelStatus
from app.deps import get_channel_service
from app.integrations.websub.subscription_service import websub_service
from app.services.channel_service import ChannelService


router = APIRouter()


async def _bg_sync_channel(channel_id: int) -> None:
    if not await is_api_available():
        logger.warning(
            "No YouTube API available, skipping sync for channel_id={}", channel_id
        )
        return

    api_key = await get_api_key()
    if not api_key:
        return

    yt_service = get_youtube_sync_service()
    async with session_scope() as session:
        ch = await session.get(Channel, channel_id)
        if not ch:
            logger.warning("Channel {} not found during bg sync", channel_id)
            return
        await yt_service.sync_channel_videos(session, ch, full_refresh=True)
        logger.info("Video sync completed for channel_id={}", channel_id)

    callback_url = settings.websub_callback_url
    if not callback_url:
        logger.debug("WebSub callback_url not configured, skipping subscription")
        return

    async with session_scope() as session:
        ch = await session.get(Channel, channel_id)
        if ch:
            await websub_service.subscribe_channel(
                ch.channel_id,
                callback_url,
                secret=settings.websub_secret or None,
            )
            logger.info("WebSub subscription registered for channel_id={}", channel_id)


@router.post("/", response_model=ChannelResponse)
async def create_channel(
    channel_in: ChannelCreate,
    background_tasks: BackgroundTasks,
    service: ChannelService = Depends(get_channel_service),
    _: User = AdminUser,
):
    db_channel = await service.create_channel(channel_in)

    if db_channel.platform == Platform.YOUTUBE:
        background_tasks.add_task(_bg_sync_channel, db_channel.id)

    return db_channel


@router.get("/", response_model=List[ChannelResponse])
async def get_channels(
    platform: Optional[str] = None,
    is_active: Optional[bool] = None,
    org_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db_session),
    ctx: PlatformContext = PlatformGuardDep,
):
    query = select(Channel)
    query = ctx.apply_platform_filter(query, Channel.platform)

    if platform:
        ctx.assert_platform_access(platform)
        query = query.where(Channel.platform == platform)
    if is_active is not None:
        query = query.where(Channel.is_active == is_active)
    if org_id is not None:
        query = query.where(Channel.org_id == org_id)

    result = await db.execute(query)
    channels = result.scalars().all()

    if not channels:
        return []

    status_map = {}
    if ctx.user_id:
        channel_ids = [ch.id for ch in channels]

        user_channel_query = select(UserChannel).where(
            UserChannel.user_id == ctx.user_id, UserChannel.channel_id.in_(channel_ids)
        )
        uc_result = await db.execute(user_channel_query)
        status_map = {uc.channel_id: uc.status for uc in uc_result.scalars().all()}

    return [
        _with_user_status(ChannelResponse.model_validate(ch), status_map.get(ch.id))
        for ch in channels
    ]


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel_by_id(
    channel_id: int,
    db: AsyncSession = Depends(get_db_session),
    ctx: PlatformContext = PlatformGuardDep,
):
    channel = await _get_or_404(db, channel_id)
    ctx.assert_platform_access(channel.platform)

    resp = ChannelResponse.model_validate(channel)
    if ctx.user_id:
        result = await db.execute(
            select(UserChannel).where(
                UserChannel.user_id == ctx.user_id,
                UserChannel.channel_id == channel_id,
            )
        )
        uc = result.scalar_one_or_none()
        if uc:
            resp.is_liked = uc.status == UserChannelStatus.LIKED
            resp.is_blocked = uc.status == UserChannelStatus.BLOCKED
    return resp


@router.put("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: int,
    channel_update: ChannelUpdate,
    db: AsyncSession = Depends(get_db_session),
    _: User = AdminUser,
):
    channel = await _get_or_404(db, channel_id)
    for key, value in channel_update.model_dump(exclude_unset=True).items():
        setattr(channel, key, value)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.delete("/{channel_id}")
async def delete_channel(
    channel_id: int,
    service: ChannelService = Depends(get_channel_service),
    _: User = AdminUser,
):
    await service.delete_channel_completely(channel_id)
    return {"message": "Channel deleted successfully"}


@router.post("/{channel_id}/refresh", response_model=ChannelResponse)
async def refresh_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db_session),
    _: User = AdminUser,
):
    channel = await _get_or_404(db, channel_id)
    if channel.platform == Platform.YOUTUBE:
        yt_service = get_youtube_sync_service()
        details = await yt_service.get_channel_info(channel.channel_id)
        if details:
            for field in ("banner_url", "description", "youtube_url"):
                if details.get(field):
                    setattr(channel, field, details[field])
            await db.commit()
            await db.refresh(channel)
    return channel


async def _get_or_404(db: AsyncSession, channel_id: int) -> Channel:
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


def _with_user_status(resp: ChannelResponse, status: Optional[str]) -> ChannelResponse:
    resp.is_liked = status == UserChannelStatus.LIKED
    resp.is_blocked = status == UserChannelStatus.BLOCKED
    return resp
