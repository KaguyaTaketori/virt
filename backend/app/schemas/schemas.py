from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.models import Platform, StreamStatus


class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    created_at: datetime
    roles: Optional[list[str]] = []

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class PermissionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    resource: str
    action: str

    class Config:
        from_attributes = True


class UserRoleUpdate(BaseModel):
    role_ids: list[int]


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


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
    banner_url: Optional[str] = None
    twitter_url: Optional[str] = None
    youtube_url: Optional[str] = None
    description: Optional[str] = None


class ChannelCreate(ChannelBase):
    pass


class ChannelResponse(ChannelBase):
    id: int
    org_id: Optional[int] = None
    banner_url: Optional[str] = None
    twitter_url: Optional[str] = None
    youtube_url: Optional[str] = None
    description: Optional[str] = None
    is_liked: Optional[bool] = False
    is_blocked: Optional[bool] = False
    bilibili_sign: Optional[str] = None
    bilibili_fans: Optional[int] = None
    bilibili_archive_count: Optional[int] = None

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
    channel_avatar_shape: Optional[str] = None  # 新增
    org_id: Optional[int] = None  # 新增

    class Config:
        from_attributes = True


class VideoResponse(BaseModel):
    id: str
    title: str
    thumbnail_url: Optional[str] = None
    duration: Optional[str] = None
    view_count: int = 0
    published_at: Optional[str] = None
    status: str


class PaginatedVideosResponse(BaseModel):
    videos: list[VideoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
