from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.models import Platform, StreamStatus


class ChannelBase(BaseModel):
    platform: Platform
    channel_id: str
    name: str
    avatar_url: Optional[str] = None
    is_active: bool = True


class ChannelUpdate(BaseModel):
    platform: Optional[Platform] = None
    channel_id: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None


class ChannelCreate(ChannelBase):
    pass


class ChannelResponse(ChannelBase):
    id: int

    class Config:
        from_attributes = True


class StreamBase(BaseModel):
    platform: Platform
    video_id: Optional[str] = None
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None
    viewer_count: int = 0
    status: StreamStatus = StreamStatus.OFFLINE
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    live_chat_id: Optional[str] = None


class StreamCreate(StreamBase):
    channel_id: int


class StreamResponse(StreamBase):
    id: int
    channel_id: int
    channel_name: Optional[str] = None
    channel_avatar: Optional[str] = None

    class Config:
        from_attributes = True
