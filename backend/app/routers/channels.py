from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

import httpx

from app.deps import get_db
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
from app.services.bilibili_fetcher import (
    get_user_info as fetch_bilibili_user_info,
    sync_bilibili_channel_videos,
)
from app.auth import get_current_user_optional
from app.config import settings
from app.services.permissions import get_user_roles

router = APIRouter(prefix="/api/channels", tags=["channels"])


# ── 辅助函数 ──────────────────────────────────────────────────────────────────


def _apply_user_status(
    response: ChannelResponse,
    db: Session,
    user_id: Optional[int],
) -> ChannelResponse:
    """将当前用户对频道的 liked/blocked 状态附加到响应对象。"""
    if not user_id:
        return response
    uc = (
        db.query(UserChannel)
        .filter(
            UserChannel.user_id == user_id,
            UserChannel.channel_id == response.id,
        )
        .first()
    )
    if uc:
        response.is_liked = uc.status == "liked"
        response.is_blocked = uc.status == "blocked"
    return response


# ── 路由 ──────────────────────────────────────────────────────────────────────


@router.get("", response_model=List[ChannelResponse])
def get_channels(
    platform: Optional[str] = None,
    is_active: Optional[bool] = None,
    org_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    query = db.query(Channel)
    if platform:
        query = query.filter(Channel.platform == platform)
    if is_active is not None:
        query = query.filter(Channel.is_active == is_active)
    if org_id is not None:
        query = query.filter(Channel.org_id == org_id)

    channels = query.all()

    if not current_user:
        return channels

    # 批量加载用户状态，避免 N+1
    user_channels = (
        db.query(UserChannel).filter(UserChannel.user_id == current_user.id).all()
    )
    status_map = {uc.channel_id: uc.status for uc in user_channels}

    result = []
    for ch in channels:
        resp = ChannelResponse.model_validate(ch)
        st = status_map.get(ch.id)
        resp.is_liked = st == "liked"
        resp.is_blocked = st == "blocked"
        result.append(resp)
    return result


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    response = ChannelResponse.model_validate(channel)

    if channel.platform == Platform.BILIBILI:
        if not current_user:
            raise HTTPException(status_code=403, detail="B站功能需要登录后访问")
        roles = get_user_roles(current_user.id, db)
        if not any(r in roles for r in ["superadmin", "admin", "operator", "user"]):
            raise HTTPException(status_code=403, detail="B站功能需要注册用户权限")

        async with httpx.AsyncClient(timeout=15.0) as client:
            user_info = await fetch_bilibili_user_info(client, channel.channel_id)
            if user_info:
                response.bilibili_sign = user_info.get("sign")
                response.bilibili_fans = user_info.get("follower")
                response.bilibili_archive_count = user_info.get("archive_count")
                if not response.avatar_url:
                    response.avatar_url = user_info.get("avatar_url")
                if not response.name:
                    response.name = user_info.get("name")

    return _apply_user_status(response, db, current_user.id if current_user else None)


@router.get("/{channel_id}/videos", response_model=PaginatedVideosResponse)
async def get_channel_videos(
    channel_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    status: Optional[str] = Query(
        None, description="Filter: live/upcoming/archive/upload/short"
    ),
    db: Session = Depends(get_db),
):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.platform == Platform.YOUTUBE:
        return await fetch_channel_videos(channel.id, page, page_size, status)

    if channel.platform == Platform.BILIBILI:
        # 首次访问时自动同步
        if not db.query(Video).filter(Video.channel_id == channel_id).count():
            await sync_bilibili_channel_videos(db, channel_id, channel.channel_id)

        query = db.query(Video).filter(Video.channel_id == channel_id)
        if status:
            query = query.filter(Video.status == status)

        total = query.count()
        total_pages = (total + page_size - 1) // page_size if total else 0
        videos_db = (
            query.order_by(Video.published_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

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
    db: Session = Depends(get_db),
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

    if db.query(Channel).filter(Channel.channel_id == resolved_channel_id).first():
        raise HTTPException(status_code=400, detail="Channel already exists")

    channel.channel_id = resolved_channel_id
    channel_data = channel.model_dump()

    if channel_details:
        for field in ("banner_url", "description", "twitter_url", "youtube_url"):
            if not channel_data.get(field) and channel_details.get(field):
                channel_data[field] = channel_details[field]

    db_channel = Channel(**channel_data)
    db.add(db_channel)
    db.commit()
    db.refresh(db_channel)

    # 新增 YouTube 频道后后台异步回填 + WebSub 订阅
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
def update_channel(
    channel_id: int,
    channel_update: ChannelUpdate,
    db: Session = Depends(get_db),
):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    for key, value in channel_update.model_dump(exclude_unset=True).items():
        setattr(channel, key, value)

    db.commit()
    db.refresh(channel)
    return channel


@router.delete("/{channel_id}")
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    from app.models.models import Stream, Danmaku

    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    db.query(Video).filter(Video.channel_id == channel_id).delete(
        synchronize_session=False
    )
    db.query(UserChannel).filter(UserChannel.channel_id == channel_id).delete(
        synchronize_session=False
    )
    db.query(Danmaku).filter(
        Danmaku.stream_id.in_(
            db.query(Stream.id).filter(Stream.channel_id == channel_id)
        )
    ).delete(synchronize_session=False)
    db.query(Stream).filter(Stream.channel_id == channel_id).delete(
        synchronize_session=False
    )
    db.delete(channel)
    db.commit()
    return {"message": "Channel deleted successfully"}


@router.post("/{channel_id}/refresh", response_model=ChannelResponse)
async def refresh_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.platform == Platform.YOUTUBE:
        details = await get_channel_details(channel.channel_id)
        if details:
            for field in ("banner_url", "description", "twitter_url", "youtube_url"):
                if details.get(field):
                    setattr(channel, field, details[field])
            db.commit()
            db.refresh(channel)

    return channel
