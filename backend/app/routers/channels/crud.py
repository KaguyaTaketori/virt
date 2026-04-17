from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.loguru_config import logger
from app.database import session_scope
from app.deps import get_db_session, get_channel_repo, get_user_channel_repo
from app.deps.guards import AdminUser
from app.deps.platform_guard import PlatformContext, PlatformGuardDep
from app.models.models import Channel, Platform, User
from app.schemas.schemas import ChannelCreate, ChannelResponse, ChannelUpdate
from app.integrations.youtube import get_youtube_sync_service
from app.services.api_key_manager import get_api_key, is_api_available
from app.constants import UserChannelStatus
from app.deps import get_channel_service
from app.integrations.websub.subscription_service import websub_service
from app.services.channel_service import ChannelService
from app.repositories import ChannelRepository, UserChannelRepository


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
    channel_repo: ChannelRepository = Depends(get_channel_repo),
    user_channel_repo: UserChannelRepository = Depends(get_user_channel_repo),
):
    channels = await channel_repo.get_multi()

    if not channels:
        return []

    channels = [ch for ch in channels if ctx.is_platform_allowed(ch.platform)]

    if platform:
        ctx.assert_platform_access(platform)
        channels = [ch for ch in channels if ch.platform == platform]
    if is_active is not None:
        channels = [ch for ch in channels if ch.is_active == is_active]
    if org_id is not None:
        channels = [ch for ch in channels if ch.org_id == org_id]

    status_map = {}
    if ctx.user_id:
        channel_ids = [ch.id for ch in channels]
        user_channels = await user_channel_repo.get_multi_by_user_and_channels(
            ctx.user_id, channel_ids
        )
        status_map = {uc.channel_id: uc.status for uc in user_channels}

    return [
        _with_user_status(ChannelResponse.model_validate(ch), status_map.get(ch.id))
        for ch in channels
    ]


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel_by_id(
    channel_id: int,
    db: AsyncSession = Depends(get_db_session),
    ctx: PlatformContext = PlatformGuardDep,
    channel_repo: ChannelRepository = Depends(get_channel_repo),
    user_channel_repo: UserChannelRepository = Depends(get_user_channel_repo),
):
    channel = await channel_repo.get(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    ctx.assert_platform_access(channel.platform)

    resp = ChannelResponse.model_validate(channel)
    if ctx.user_id:
        uc = await user_channel_repo.get_by_user_and_channel(ctx.user_id, channel_id)
        if uc:
            resp.is_liked = uc.status == UserChannelStatus.LIKED
            resp.is_blocked = uc.status == UserChannelStatus.BLOCKED
    return resp


@router.put("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: int,
    channel_update: ChannelUpdate,
    db: AsyncSession = Depends(get_db_session),
    channel_repo: ChannelRepository = Depends(get_channel_repo),
    _: User = AdminUser,
):
    channel = await channel_repo.get(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    update_data = channel_update.model_dump(exclude_unset=True)
    if update_data:
        channel = await channel_repo.update(channel_id, update_data)

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
    channel_repo: ChannelRepository = Depends(get_channel_repo),
    _: User = AdminUser,
):
    channel = await channel_repo.get(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

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


def _with_user_status(resp: ChannelResponse, status: Optional[str]) -> ChannelResponse:
    resp.is_liked = status == UserChannelStatus.LIKED
    resp.is_blocked = status == UserChannelStatus.BLOCKED
    return resp
