from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.models import Platform, StreamStatus


class OrganizationBase(BaseModel):
    name: str
    name_en: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    logo_shape: Optional[str] = "circle"  # circle or square


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    name_en: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    logo_shape: Optional[str] = None


class OrganizationResponse(OrganizationBase):
    id: int

    class Config:
        from_attributes = True


class ChannelBase(BaseModel):
    platform: Platform
    channel_id: str
    name: str
    avatar_url: Optional[str] = None
    is_active: bool = True
    org_id: Optional[int] = None
    avatar_shape: Optional[str] = "circle"  # circle or square


class ChannelUpdate(BaseModel):
    platform: Optional[Platform] = None
    channel_id: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    org_id: Optional[int] = None
    avatar_shape: Optional[str] = None


class ChannelCreate(ChannelBase):
    pass


class ChannelResponse(ChannelBase):
    id: int
    org_id: Optional[int] = None

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
