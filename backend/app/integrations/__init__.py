from __future__ import annotations

from app.integrations.urls import (
    IframeUrlGenerator,
    build_bilibili_url,
    build_youtube_url,
    validate_safe_url,
)
from app.integrations.bili_client import BiliClient, get_bili_client, bili_client_dep
from app.integrations.youtube import (
    YouTubeApiClient,
    YouTubeSyncService,
    VideoParser,
    get_yt_api_client,
    get_yt_parser,
    get_youtube_sync_service,
)
from app.integrations.api_client import (
    BaseAPIClient,
    BilibiliAPIClient,
    YouTubeAPIClient,
)

__all__ = [
    "BiliClient",
    "get_bili_client",
    "bili_client_dep",
    "YouTubeApiClient",
    "YouTubeSyncService",
    "VideoParser",
    "get_yt_api_client",
    "get_yt_parser",
    "get_youtube_sync_service",
    "BaseAPIClient",
    "BilibiliAPIClient",
    "YouTubeAPIClient",
    "IframeUrlGenerator",
    "build_youtube_url",
    "build_bilibili_url",
    "validate_safe_url",
]
