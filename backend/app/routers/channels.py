from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import SessionLocal
from app.schemas.schemas import ChannelCreate, ChannelResponse, ChannelUpdate
from app.models.models import Channel, Platform
from app.services.youtube_channel import get_youtube_channel_info

router = APIRouter(prefix="/api/channels", tags=["channels"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=List[ChannelResponse])
def get_channels(
    platform: str = None, is_active: bool = None, db: Session = Depends(get_db)
):
    query = db.query(Channel)
    if platform:
        query = query.filter(Channel.platform == platform)
    if is_active is not None:
        query = query.filter(Channel.is_active == is_active)
    return query.all()


@router.get("/{channel_id}", response_model=ChannelResponse)
def get_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.post("", response_model=ChannelResponse)
async def create_channel(channel: ChannelCreate, db: Session = Depends(get_db)):
    # 解析 YouTube 频道输入（支持 @username, 自定义URL, channel_id）
    resolved_channel_id = None
    if channel.platform == Platform.YOUTUBE:
        channel_info = await get_youtube_channel_info(channel.channel_id)
        if channel_info and channel_info.get("channel_id"):
            resolved_channel_id = channel_info["channel_id"]
            # 如果没有提供头像，使用 API 获取的
            if not channel.avatar_url and channel_info.get("avatar_url"):
                channel.avatar_url = channel_info["avatar_url"]
            # 如果没有提供名称，使用 API 获取的
            if not channel.name and channel_info.get("title"):
                channel.name = channel_info["title"]
        else:
            # 解析失败，尝试直接使用输入
            resolved_channel_id = channel.channel_id
    else:
        resolved_channel_id = channel.channel_id

    # 检查是否已存在
    existing = (
        db.query(Channel).filter(Channel.channel_id == resolved_channel_id).first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Channel already exists")

    # 更新为解析后的 channel_id
    channel.channel_id = resolved_channel_id

    db_channel = Channel(**channel.model_dump())
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
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    db.delete(channel)
    db.commit()
    return {"message": "Channel deleted successfully"}
