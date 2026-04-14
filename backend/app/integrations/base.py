from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from app.models.models import Platform


class LiveStatusEnum(str, Enum):
    LIVE = "live"
    UPCOMING = "upcoming"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class ChannelInfo:
    platform: Platform
    channel_id: str
    name: str
    avatar_url: Optional[str] = None
    banner_url: Optional[str] = None
    description: Optional[str] = None
    twitter_url: Optional[str] = None
    youtube_url: Optional[str] = None
    bilibili_sign: Optional[str] = None
    bilibili_fans: Optional[int] = None
    bilibili_archive_count: Optional[int] = None
    bilibili_face: Optional[str] = None


@dataclass
class LiveStatus:
    video_id: Optional[str]
    title: Optional[str]
    thumbnail_url: Optional[str]
    status: LiveStatusEnum
    viewer_count: int = 0
    started_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None


@dataclass
class VideoItem:
    id: str
    title: str
    thumbnail_url: Optional[str]
    duration: Optional[str]
    view_count: int
    published_at: Optional[datetime]
    status: str


@dataclass
class PaginatedVideos:
    videos: list[VideoItem]
    total: int
    page: int
    page_size: int
    total_pages: int


from typing import Protocol, Any


class PlatformClient(Protocol):
    @property
    def platform(self) -> Platform: ...

    async def get_channel_info(self, channel_id: str) -> Optional[Any]: ...
    async def get_live_status(self, channel_id: str) -> Optional[Any]: ...
    async def batch_get_live_status(
        self, channel_ids: list[str], max_concurrent: int = 5
    ) -> dict[str, Optional[Any]]: ...
    async def get_videos(
        self,
        channel_id: str,
        page: int = 1,
        page_size: int = 24,
        status_filter: Optional[str] = None,
    ) -> Optional[Any]: ...

    async def resolve_channel_id(self, input_str: str) -> Optional[str]:
        raise NotImplementedError("Optional method")

    def generate_embed_url(self, video_id: str) -> str:
        raise NotImplementedError("Optional method")

    def normalize_video_id(self, video_id: str) -> str:
        raise NotImplementedError("Optional method")
