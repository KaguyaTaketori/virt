import re

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from app.models.models import Platform, StreamStatus, User


class UserCreate(BaseModel):
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50, 
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="用户名只能包含字母、数字、下划线和减号，长度为3-50"
    )
    email: Optional[EmailStr] = Field(None, description="可选的合法邮箱地址")
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=128,
        description="密码长度需在8-128位之间"
    )

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError("密码必须包含至少一个大写字母")
        if not re.search(r"[a-z]", value):
            raise ValueError("密码必须包含至少一个小写字母")
        if not re.search(r"[0-9]", value):
            raise ValueError("密码必须包含至少一个数字")
            
        return value


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    created_at: datetime
    roles: set[str] = set()
    permissions: list[str] = []

    @classmethod
    def from_orm_with_roles(cls, user: "User") -> "UserResponse":
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at,
            roles={ur.role.name for ur in user.user_roles},
        )

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
    name: str = Field(..., min_length=1, max_length=100)
    name_en: Optional[str] = Field(None, max_length=100)
    logo_url: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=200)
    logo_shape: Optional[str] = Field("circle", pattern="^(circle|square)$")
 
    @field_validator("website", mode="before")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if not v.startswith(("http://", "https://")):
            raise ValueError("Website must start with http:// or https://")
        return v


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    name_en: Optional[str] = Field(None, max_length=100)
    logo_url: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=200)
    logo_shape: Optional[str] = Field(None, pattern="^(circle|square)$")


class OrganizationResponse(OrganizationBase):
    id: int

    class Config:
        from_attributes = True


class ChannelBase(BaseModel):
    platform: Platform
    channel_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    is_active: bool = True
    org_id: Optional[int] = None
    avatar_shape: Optional[str] = Field("circle", pattern="^(circle|square)$")
    twitter_url: Optional[str] = Field(None, max_length=200)
    youtube_url: Optional[str] = Field(None, max_length=200)
    twitch_url: Optional[str] = Field(None, max_length=200)
    group: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field("active", max_length=20)
 
    @field_validator("channel_id", mode="before")
    @classmethod
    def sanitize_channel_id(cls, v: str) -> str:
        if not v:
            raise ValueError("channel_id cannot be empty")
        v = v.strip()
        if v.startswith("http://") or v.startswith("https://"):
            return v
        if any(c in v for c in ("../", "..\\", "\x00", "\n", "\r")):
            raise ValueError("channel_id contains invalid characters")
        return v
 
    @field_validator("twitter_url", "youtube_url", "twitch_url", mode="before")
    @classmethod
    def validate_social_urls(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class ChannelUpdate(BaseModel):
    platform: Optional[Platform] = None
    channel_id: Optional[str] = Field(None, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    org_id: Optional[int] = None
    avatar_shape: Optional[str] = Field(None, pattern="^(circle|square)$")
    banner_url: Optional[str] = Field(None, max_length=500)
    twitter_url: Optional[str] = Field(None, max_length=200)
    youtube_url: Optional[str] = Field(None, max_length=200)
    twitch_url: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    group: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=20)


class ChannelCreate(ChannelBase):
    pass


class ChannelResponse(ChannelBase):
    id: int
    org_id: Optional[int] = None
    banner_url: Optional[str] = None
    twitter_url: Optional[str] = None
    youtube_url: Optional[str] = None
    twitch_url: Optional[str] = None
    description: Optional[str] = None
    group: Optional[str] = None
    status: Optional[str] = "active"
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
