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
from app.integrations.youtube import YouTubePlatform

try:
    from app.integrations.bilibili import BilibiliPlatform
except ImportError:
    BilibiliPlatform = None

try:
    from app.integrations.youtube import youtube_platform
except ImportError:
    youtube_platform = None

try:
    from app.integrations.bilibili import bilibili_platform
except ImportError:
    bilibili_platform = None

__all__ = [
    "BaseLivePlatform",
    "ChannelInfo",
    "LiveStatus",
    "LiveStatusEnum",
    "PaginatedVideos",
    "VideoItem",
    "YouTubePlatform",
    "BilibiliPlatform",
    "youtube_platform",
    "bilibili_platform",
    "IframeUrlGenerator",
    "build_youtube_url",
    "build_bilibili_url",
    "validate_safe_url",
]
