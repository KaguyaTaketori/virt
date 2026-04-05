from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database_async import AsyncSessionFactory
from app.deps import get_async_db
from app.deps.guards import AdminUser
from app.deps.platform_guard import PlatformContext, PlatformGuardDep
from app.models.models import (
    Channel,
    Danmaku,
    Platform,
    Stream,
    User,
    UserChannel,
    Video,
)
from app.schemas.schemas import ChannelCreate, ChannelResponse, ChannelUpdate
from app.services.youtube_channel import get_channel_details, get_youtube_channel_info
from app.services.youtube_sync import sync_channel_videos
from app.services.youtube_websub import subscribe_channel
from app.services.api_key_manager import get_api_key, is_api_available

router = APIRouter()


@router.get("/", response_model=List[ChannelResponse])
async def get_channels(
    platform: Optional[str] = None,
    is_active: Optional[bool] = None,
    org_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
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

    if not ctx.user_id:
        return channels

    result = await db.execute(
        select(UserChannel).where(UserChannel.user_id == ctx.user_id)
    )
    status_map = {uc.channel_id: uc.status for uc in result.scalars().all()}

    return [
        _with_user_status(ChannelResponse.model_validate(ch), status_map.get(ch.id))
        for ch in channels
    ]


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel_by_id(
    channel_id: int,
    db: AsyncSession = Depends(get_async_db),
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
            resp.is_liked = uc.status == "liked"
            resp.is_blocked = uc.status == "blocked"
    return resp


@router.post("/", response_model=ChannelResponse)
async def create_channel(
    channel: ChannelCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    _: User = AdminUser,
):
    resolved_id = channel.channel_id
    details: Optional[dict] = None

    if channel.platform == Platform.YOUTUBE:
        info = await get_youtube_channel_info(channel.channel_id)
        if info and info.get("channel_id"):
            resolved_id = info["channel_id"]
            if not channel.avatar_url and info.get("avatar_url"):
                channel.avatar_url = info["avatar_url"]
            if not channel.name and info.get("title"):
                channel.name = info["title"]
        details = await get_channel_details(resolved_id)

    existing = await db.execute(
        select(Channel).where(Channel.channel_id == resolved_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Channel already exists")

    channel.channel_id = resolved_id
    data = channel.model_dump()
    if details:
        for field in ("banner_url", "description", "twitter_url", "youtube_url"):
            if not data.get(field) and details.get(field):
                data[field] = details[field]

    db_channel = Channel(**data)
    db.add(db_channel)
    await db.commit()
    await db.refresh(db_channel)

    if db_channel.platform == Platform.YOUTUBE:
        channel_id = db_channel.id
        api_key = await get_api_key()
        callback_url = settings.websub_callback_url

        async def _bg_sync():
            async with AsyncSessionFactory() as session:
                ch = await session.get(Channel, channel_id)
                if not ch or not api_key:
                    return
                await sync_channel_videos(session, ch, api_key, full_refresh=True)
                if (
                    callback_url
                    and callback_url != "https://your-domain.com/api/websub/youtube"
                ):
                    await subscribe_channel(
                        ch.channel_id,
                        callback_url,
                        secret=settings.websub_secret or None,
                    )

        background_tasks.add_task(_bg_sync)

    return db_channel


@router.put("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: int,
    channel_update: ChannelUpdate,
    db: AsyncSession = Depends(get_async_db),
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
    db: AsyncSession = Depends(get_async_db),
    _: User = AdminUser,
):
    channel = await _get_or_404(db, channel_id)

    for model, fk_col in [
        (Video, Video.channel_id),
        (UserChannel, UserChannel.channel_id),
    ]:
        result = await db.execute(select(model).where(fk_col == channel_id))
        for row in result.scalars().all():
            await db.delete(row)

    result = await db.execute(select(Stream).where(Stream.channel_id == channel_id))
    for stream in result.scalars().all():
        dm_result = await db.execute(
            select(Danmaku).where(Danmaku.stream_id == stream.id)
        )
        for dm in dm_result.scalars().all():
            await db.delete(dm)
        await db.delete(stream)

    await db.delete(channel)
    await db.commit()
    return {"message": "Channel deleted successfully"}


@router.post("/{channel_id}/refresh", response_model=ChannelResponse)
async def refresh_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: User = AdminUser,
):
    channel = await _get_or_404(db, channel_id)
    if channel.platform == Platform.YOUTUBE:
        details = await get_channel_details(channel.channel_id)
        if details:
            for field in ("banner_url", "description", "twitter_url", "youtube_url"):
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
    resp.is_liked = status == "liked"
    resp.is_blocked = status == "blocked"
    return resp
