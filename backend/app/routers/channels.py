from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import SessionLocal
from app.schemas.schemas import (
    ChannelCreate,
    ChannelResponse,
    ChannelUpdate,
    PaginatedVideosResponse,
    VideoResponse,
)
from app.models.models import Channel, Platform, User, UserChannel
from app.services.youtube_channel import get_youtube_channel_info, get_channel_details
from app.services.youtube_videos import get_channel_videos as fetch_channel_videos
from app.auth import get_current_user_optional, get_db

router = APIRouter(prefix="/api/channels", tags=["channels"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=List[ChannelResponse])
def get_channels(
    platform: str = None,
    is_active: bool = None,
    org_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    query = db.query(Channel)
    if platform:
        query = query.filter(Channel.platform == platform)
    if is_active is not None:
        query = query.filter(Channel.is_active == is_active)
    if org_id is not None:
        query = query.filter(Channel.org_id == org_id)

    channels = query.all()

    if current_user:
        user_channels = (
            db.query(UserChannel).filter(UserChannel.user_id == current_user.id).all()
        )
        user_channel_map = {uc.channel_id: uc.status for uc in user_channels}

        result = []
        for ch in channels:
            response = ChannelResponse.model_validate(ch)
            status = user_channel_map.get(ch.id)
            response.is_liked = status == "liked"
            response.is_blocked = status == "blocked"
            result.append(response)
        return result

    return channels


def _add_user_status_to_channel(channel: Channel, db: Session, user_id: int = None):
    response = ChannelResponse.model_validate(channel)
    if user_id:
        user_channel = (
            db.query(UserChannel)
            .filter(
                UserChannel.user_id == user_id,
                UserChannel.channel_id == channel.id,
            )
            .first()
        )
        if user_channel:
            response.is_liked = user_channel.status == "liked"
            response.is_blocked = user_channel.status == "blocked"
    return response


@router.get("/{channel_id}", response_model=ChannelResponse)
def get_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    user_id = current_user.id if current_user else None
    return _add_user_status_to_channel(channel, db, user_id)


@router.get("/{channel_id}/videos", response_model=PaginatedVideosResponse)
async def get_channel_videos(
    channel_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    status: str = Query(None, description="Filter by status: live, upcoming, archive"),
    db: Session = Depends(get_db),
):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.platform == Platform.YOUTUBE:
        result = await fetch_channel_videos(channel.id, page, page_size, status)
        return result
    else:
        return PaginatedVideosResponse(
            videos=[], total=0, page=page, page_size=page_size, total_pages=0
        )


@router.post("", response_model=ChannelResponse)
async def create_channel(channel: ChannelCreate, db: Session = Depends(get_db)):
    resolved_channel_id = None
    channel_details = None

    if channel.platform == Platform.YOUTUBE:
        channel_info = await get_youtube_channel_info(channel.channel_id)
        if channel_info and channel_info.get("channel_id"):
            resolved_channel_id = channel_info["channel_id"]
            if not channel.avatar_url and channel_info.get("avatar_url"):
                channel.avatar_url = channel_info["avatar_url"]
            if not channel.name and channel_info.get("title"):
                channel.name = channel_info["title"]
        else:
            resolved_channel_id = channel.channel_id

        channel_details = await get_channel_details(resolved_channel_id)
    else:
        resolved_channel_id = channel.channel_id

    existing = (
        db.query(Channel).filter(Channel.channel_id == resolved_channel_id).first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Channel already exists")

    channel.channel_id = resolved_channel_id

    channel_data = channel.model_dump()

    if channel_details:
        if not channel_data.get("banner_url") and channel_details.get("banner_url"):
            channel_data["banner_url"] = channel_details["banner_url"]
        if not channel_data.get("description") and channel_details.get("description"):
            channel_data["description"] = channel_details["description"]
        if not channel_data.get("twitter_url") and channel_details.get("twitter_url"):
            channel_data["twitter_url"] = channel_details["twitter_url"]
        if not channel_data.get("youtube_url") and channel_details.get("youtube_url"):
            channel_data["youtube_url"] = channel_details["youtube_url"]

    db_channel = Channel(**channel_data)
    db.add(db_channel)
    db.commit()
    db.refresh(db_channel)
    return db_channel


@router.put("/{channel_id}", response_model=ChannelResponse)
def update_channel(
    channel_id: int, channel_update: ChannelUpdate, db: Session = Depends(get_db)
):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    update_data = channel_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
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

    # 先删除相关的 streams 和 danmakus
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
            if details.get("banner_url"):
                channel.banner_url = details["banner_url"]
            if details.get("description"):
                channel.description = details["description"]
            if details.get("twitter_url"):
                channel.twitter_url = details["twitter_url"]
            if details.get("youtube_url"):
                channel.youtube_url = details["youtube_url"]
            db.commit()
            db.refresh(channel)

    return channel
