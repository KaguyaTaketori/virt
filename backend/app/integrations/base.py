from __future__ import annotations

from abc import ABC, abstractmethod
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
    follower_count: Optional[int] = None
    bio: Optional[str] = None
    video_count: Optional[int] = None
    following_count: Optional[int] = None
    extra_info: Optional[dict] = None


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


class BaseLivePlatform(ABC):
    PLATFORM: Platform

    @property
    def platform(self) -> Platform:
        return self.PLATFORM

    @abstractmethod
    async def get_channel_info(self, channel_id: str) -> Optional[ChannelInfo]:
        """获取频道基本信息"""
        raise NotImplementedError

    @abstractmethod
    async def resolve_channel_id(self, input_str: str) -> Optional[str]:
        """从URL/handle解析出频道ID"""
        raise NotImplementedError

    @abstractmethod
    async def get_live_status(self, channel_id: str) -> Optional[LiveStatus]:
        """获取单个频道的直播状态"""
        raise NotImplementedError

    @abstractmethod
    async def batch_get_live_status(
        self, channel_ids: list[str], max_concurrent: int = 5
    ) -> dict[str, Optional[LiveStatus]]:
        """批量获取多个频道的直播状态"""
        raise NotImplementedError

    @abstractmethod
    async def get_videos(
        self,
        channel_id: str,
        page: int = 1,
        page_size: int = 24,
        status_filter: Optional[str] = None,
    ) -> PaginatedVideos:
        """获取频道视频列表"""
        raise NotImplementedError

    @abstractmethod
    def generate_embed_url(self, video_id: str) -> str:
        """生成 iframe 嵌入 URL"""
        raise NotImplementedError

    @abstractmethod
    def normalize_video_id(self, video_id: str) -> str:
        """标准化视频ID格式"""
        raise NotImplementedError
