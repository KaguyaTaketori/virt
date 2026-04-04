from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.deps import get_async_db
from app.deps.permissions import AdminUser, require_permission_dep
from app.database_async import AsyncSessionFactory
from app.schemas.schemas import (
    ChannelCreate,
    ChannelResponse,
    ChannelUpdate,
    PaginatedVideosResponse,
    VideoResponse,
)
from app.models.models import Channel, Platform, User, UserChannel, Video
from app.services.youtube_channel import get_youtube_channel_info, get_channel_details
from app.services.youtube_videos import get_channel_videos as fetch_channel_videos
from app.services.youtube_sync import sync_channel_videos
from app.services.youtube_websub import subscribe_channel
from app.services.bilibili_fetcher import sync_bilibili_channel_videos
from app.services.bilibili_channel import bilibili_channel_service
from app.auth import get_current_user_optional
from app.config import settings
from app.services.permissions import has_permission
from app.services.scraper import sync as scraper_sync
from app.loguru_config import logger

router = APIRouter(prefix="/api/channels", tags=["channels"])


async def _apply_user_status(
    response: ChannelResponse,
    db: AsyncSession,
    user_id: Optional[int],
) -> ChannelResponse:
    if not user_id:
        return response
    result = await db.execute(
        select(UserChannel).where(
            UserChannel.user_id == user_id,
            UserChannel.channel_id == response.id,
        )
    )
    uc = result.scalar_one_or_none()
    if uc:
        response.is_liked = uc.status == "liked"
        response.is_blocked = uc.status == "blocked"
    return response


@router.get("", response_model=List[ChannelResponse])
async def get_channels(
    platform: Optional[str] = None,
    is_active: Optional[bool] = None,
    org_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    has_bilibili_perm = False
    if current_user:
        has_bilibili_perm = await has_permission(
            current_user.id, "bilibili", "access", db
        )

    query = select(Channel)
    if not has_bilibili_perm:
        query = query.where(Channel.platform == "youtube")
    if platform:
        query = query.where(Channel.platform == platform)
    if is_active is not None:
        query = query.where(Channel.is_active == is_active)
    if org_id is not None:
        query = query.where(Channel.org_id == org_id)

    result = await db.execute(query)
    channels = result.scalars().all()

    if not current_user:
        return channels

    result = await db.execute(
        select(UserChannel).where(UserChannel.user_id == current_user.id)
    )
    user_channels = result.scalars().all()
    status_map = {uc.channel_id: uc.status for uc in user_channels}

    result_list = []
    for ch in channels:
        resp = ChannelResponse.model_validate(ch)
        st = status_map.get(ch.id)
        resp.is_liked = st == "liked"
        resp.is_blocked = st == "blocked"
        result_list.append(resp)
    return result_list


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel_by_id(
    channel_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    has_bilibili_perm = False
    if current_user:
        has_bilibili_perm = await has_permission(
            current_user.id, "bilibili", "access", db
        )

    if channel.platform == Platform.BILIBILI and not has_bilibili_perm:
        raise HTTPException(status_code=403, detail="需要B站访问权限")

    resp = ChannelResponse.model_validate(channel)

    if current_user:
        result = await db.execute(
            select(UserChannel).where(
                UserChannel.user_id == current_user.id,
                UserChannel.channel_id == channel_id,
            )
        )
        uc = result.scalar_one_or_none()
        if uc:
            resp.is_liked = uc.status == "liked"
            resp.is_blocked = uc.status == "blocked"

    return resp


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
        return await fetch_channel_videos(channel.id, page, page_size, status)

    if channel.platform == Platform.BILIBILI:
        result = await db.execute(select(Video).where(Video.channel_id == channel_id))
        videos_count = len(result.scalars().all())
        if not videos_count:
            await sync_bilibili_channel_videos(db, channel_id, channel.channel_id)

        query = select(Video).where(Video.channel_id == channel_id)
        if status:
            query = query.where(Video.status == status)

        result = await db.execute(query)
        total = len(result.scalars().all())
        total_pages = (total + page_size - 1) // page_size if total else 0
        query = (
            query.order_by(Video.published_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(query)
        videos_db = result.scalars().all()

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
                for v in videos_db
            ],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    return PaginatedVideosResponse(
        videos=[], total=0, page=page, page_size=page_size, total_pages=0
    )


@router.post("", response_model=ChannelResponse)
async def create_channel(
    channel: ChannelCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    _: User = AdminUser,
):
    resolved_channel_id = channel.channel_id
    channel_details: Optional[dict] = None

    if channel.platform == Platform.YOUTUBE:
        channel_info = await get_youtube_channel_info(channel.channel_id)
        if channel_info and channel_info.get("channel_id"):
            resolved_channel_id = channel_info["channel_id"]
            if not channel.avatar_url and channel_info.get("avatar_url"):
                channel.avatar_url = channel_info["avatar_url"]
            if not channel.name and channel_info.get("title"):
                channel.name = channel_info["title"]

        channel_details = await get_channel_details(resolved_channel_id)

    result = await db.execute(
        select(Channel).where(Channel.channel_id == resolved_channel_id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Channel already exists")

    channel.channel_id = resolved_channel_id
    channel_data = channel.model_dump()

    if channel_details:
        for field in ("banner_url", "description", "twitter_url", "youtube_url"):
            if not channel_data.get(field) and channel_details.get(field):
                channel_data[field] = channel_details[field]

    db_channel = Channel(**channel_data)
    db.add(db_channel)
    await db.commit()
    await db.refresh(db_channel)

    if db_channel.platform == Platform.YOUTUBE:
        channel_id = db_channel.id
        api_key = settings.youtube_api_key
        callback_url = settings.websub_callback_url

        async def _bg_sync_and_subscribe():
            async with AsyncSessionFactory() as session:
                ch_obj = await session.get(Channel, channel_id)
                if not ch_obj:
                    return
                await sync_channel_videos(session, ch_obj, api_key, full_refresh=True)
                if (
                    callback_url
                    and callback_url != "https://your-domain.com/api/websub/youtube"
                    and api_key
                ):
                    await subscribe_channel(
                        ch_obj.channel_id,
                        callback_url,
                        secret=settings.websub_secret or None,
                    )

        background_tasks.add_task(_bg_sync_and_subscribe)

    return db_channel


@router.put("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: int,
    channel_update: ChannelUpdate,
    db: AsyncSession = Depends(get_async_db),
    _current_user: User = AdminUser,
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    for key, value in channel_update.model_dump(exclude_unset=True).items():
        setattr(channel, key, value)

    await db.commit()
    await db.refresh(channel)
    return channel


@router.delete("/{channel_id}")
async def delete_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_async_db),
    _current_user: User = AdminUser,
):
    from app.models.models import Stream, Danmaku

    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    result = await db.execute(select(Video).where(Video.channel_id == channel_id))
    for v in result.scalars().all():
        await db.delete(v)
    result = await db.execute(
        select(UserChannel).where(UserChannel.channel_id == channel_id)
    )
    for uc in result.scalars().all():
        await db.delete(uc)
    result = await db.execute(select(Stream).where(Stream.channel_id == channel_id))
    for s in result.scalars().all():
        result_dm = await db.execute(select(Danmaku).where(Danmaku.stream_id == s.id))
        for dm in result_dm.scalars().all():
            await db.delete(dm)
        await db.delete(s)
    await db.delete(channel)
    await db.commit()
    return {"message": "Channel deleted successfully"}


@router.post("/{channel_id}/refresh", response_model=ChannelResponse)
async def refresh_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_async_db),
    _current_user: User = AdminUser,
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.platform == Platform.YOUTUBE:
        details = await get_channel_details(channel.channel_id)
        if details:
            for field in ("banner_url", "description", "twitter_url", "youtube_url"):
                if details.get(field):
                    setattr(channel, field, details[field])
            await db.commit()
            await db.refresh(channel)

    return channel


@router.post(
    "/scrape/vspo",
    tags=["scraper"],
    dependencies=[Depends(require_permission_dep("channel", "manage"))],
)
async def scrape_vspo_channels(db: AsyncSession = Depends(get_async_db)):
    try:
        result = await scraper_sync.scrape_and_sync_vspo(db)
        return {"status": "success", "source": "vspo", **result}
    except Exception as e:
        logger.error("scrape_vspo error: {}", e)
        raise HTTPException(status_code=500, detail="爬取 VSPO! 失败，请查看服务日志")


@router.post(
    "/scrape/nijisanji",
    tags=["scraper"],
    dependencies=[Depends(require_permission_dep("channel", "manage"))],
)
async def scrape_nijisanji_channels(db: AsyncSession = Depends(get_async_db)):
    try:
        result = await scraper_sync.scrape_and_sync_nijisanji(db)
        return {"status": "success", "source": "nijisanji", **result}
    except Exception as e:
        logger.error("scrape_nijisanji error: {}", e)
        raise HTTPException(
            status_code=500, detail="爬取 Nijisanji 失败，请查看服务日志"
        )


@router.post(
    "/scrape/all",
    tags=["scraper"],
    dependencies=[Depends(require_permission_dep("channel", "manage"))],
)
async def scrape_all_channels(db: AsyncSession = Depends(get_async_db)):
    try:
        result = await scraper_sync.scrape_and_sync_all(db)
        return {"status": "success", **result}
    except Exception as e:
        logger.error("scrape_all error: {}", e)
        raise HTTPException(status_code=500, detail="爬取失败，请查看服务日志")


@router.get("/{channel_id}/bilibili")
async def get_channel_bilibili_info(
    channel_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.platform != Platform.BILIBILI:
        raise HTTPException(status_code=400, detail="Channel is not a Bilibili channel")

    has_bilibili_perm = False
    if current_user:
        has_bilibili_perm = await has_permission(
            current_user.id, "bilibili", "access", db
        )

    if not has_bilibili_perm:
        raise HTTPException(status_code=403, detail="需要B站访问权限")

    uid = channel.channel_id

    info, dynamics, videos = await asyncio.gather(
        bilibili_channel_service.get_info(uid),
        bilibili_channel_service.get_dynamics(uid),
        bilibili_channel_service.get_videos(uid),
    )

    return {
        "info": info,
        "dynamics": dynamics or [],
        "videos": videos or [],
    }
