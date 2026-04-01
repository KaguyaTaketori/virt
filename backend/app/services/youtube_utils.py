"""
YouTube 数据解析工具函数（共享层）。
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional


def parse_duration(iso_duration: Optional[str]) -> tuple[Optional[str], int]:
    """
    解析 ISO 8601 时长字符串（如 'PT1H23M45S'）。

    返回：
        (格式化显示字符串, 总秒数)
        示例：'PT1H23M45S' → ('1:23:45', 5025)
              'PT45S'      → ('0:45', 45)
              None         → (None, 0)
    """
    if not iso_duration:
        return None, 0

    match = re.fullmatch(
        r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        iso_duration,
    )
    if not match:
        return None, 0

    days    = int(match.group(1) or 0)
    hours   = int(match.group(2) or 0) + days * 24
    minutes = int(match.group(3) or 0)
    seconds = int(match.group(4) or 0)

    total_secs = hours * 3600 + minutes * 60 + seconds

    if hours > 0:
        fmt = f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        fmt = f"{minutes}:{seconds:02d}"

    return fmt, total_secs


def determine_video_status(item: dict, total_secs: int) -> str:
    """
    根据 YouTube API video item 精准判断视频状态。
    
    参数：
        item      — YouTube Videos.list 返回的单个视频 item dict (需要包含 snippet 和 liveStreamingDetails)
        total_secs — 已解析的视频总秒数
    """
    snippet = item.get("snippet", {})
    live_content = snippet.get("liveBroadcastContent", "none") 
    live_details = item.get("liveStreamingDetails", {})

    if 0 < total_secs <= 61:
        return "short"

    if live_content == "live":
        return "live"
    if live_content == "upcoming":
        return "upcoming"

    if live_details.get("actualEndTime"):
        return "archive"

    return "upload"


def extract_thumbnail(snippet: dict) -> Optional[str]:
    """
    按质量优先级提取封面 URL。
    优先级：maxres > standard > high > medium > default
    """
    thumbs = snippet.get("thumbnails", {})
    for quality in ("maxres", "standard", "high", "medium", "default"):
        url = thumbs.get(quality, {}).get("url")
        if url:
            return url
    return None


def parse_yt_datetime(iso_str: Optional[str]) -> Optional[datetime]:
    """
    将 YouTube 返回的 ISO 8601 时间字符串转为 aware datetime（UTC 时区）。
    Python 3.10 以下 fromisoformat 不识别 'Z'，需手动替换。
    """
    if not iso_str:
        return None
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def parse_video_item(channel_id: int, channel_platform: str, item: dict) -> dict:
    """
    将 YouTube API 的 video item dict 完整解析为可直接用于 Upsert 的字段字典。

    这是 youtube_sync.py 和 youtube_backfill.py 共同调用的统一解析入口。

    参数：
        channel_id       — 数据库 Channel.id
        channel_platform — Channel.platform（Platform 枚举）
        item             — YouTube Videos.list 返回的单个视频 item
    """
    video_id: str   = item["id"]
    snippet: dict   = item.get("snippet", {})
    content: dict   = item.get("contentDetails", {})
    stats: dict     = item.get("statistics", {})
    live: dict      = item.get("liveStreamingDetails") or {}

    duration_fmt, total_secs = parse_duration(content.get("duration"))
    status = determine_video_status(item, total_secs)

    return {
        "channel_id":      channel_id,
        "platform":        channel_platform,
        "video_id":        video_id,
        "title":           snippet.get("title"),
        "thumbnail_url":   extract_thumbnail(snippet),
        "duration":        duration_fmt,
        "duration_secs":   total_secs if total_secs > 0 else None,
        "view_count":      int(stats.get("viewCount", 0)),
        "like_count":      int(stats["likeCount"]) if stats.get("likeCount") else None,
        "status":          status,
        "published_at":    parse_yt_datetime(snippet.get("publishedAt")),
        "scheduled_at":    parse_yt_datetime(live.get("scheduledStartTime")),
        "live_started_at": parse_yt_datetime(live.get("actualStartTime")),
        "live_ended_at":   parse_yt_datetime(live.get("actualEndTime")),
        "live_chat_id":    live.get("activeLiveChatId"),
    }