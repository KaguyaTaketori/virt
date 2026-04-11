from __future__ import annotations

from app.integrations.base import (
    BaseLivePlatform,
    ChannelInfo,
    LiveStatus,
    LiveStatusEnum,
    PaginatedVideos,
    VideoItem,
)
from app.integrations.urls import (
    IframeUrlGenerator,
    build_bilibili_url,
    build_youtube_url,
    validate_safe_url,
)
from app.integrations.bili_client import BiliClient, get_bili_client, bili_client_dep
from app.integrations.youtube_client import (
    YouTubeClient,
    get_youtube_client,
    youtube_client_dep,
)
from app.integrations.api_client import (
    BaseAPIClient,
    BilibiliAPIClient,
    YouTubeAPIClient,
)

__all__ = [
    "BaseLivePlatform",
    "ChannelInfo",
    "LiveStatus",
    "LiveStatusEnum",
    "PaginatedVideos",
    "VideoItem",
    "BiliClient",
    "get_bili_client",
    "bili_client_dep",
    "YouTubeClient",
    "get_youtube_client",
    "youtube_client_dep",
    "BaseAPIClient",
    "BilibiliAPIClient",
    "YouTubeAPIClient",
    "IframeUrlGenerator",
    "build_youtube_url",
    "build_bilibili_url",
    "validate_safe_url",
]
