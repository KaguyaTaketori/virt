"""
YouTube 数据解析工具函数（共享层）。
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from app.services.constants import PREMIERE_POSITIVE_THRESHOLD, YT_LIVE_STRONG, YT_LIVE_THRESHOLD, YT_PREMIERE_LONG, YT_PREMIERE_MEDIUM, YT_PREMIERE_SHORT, YT_SHORT_MAX_SECS


def parse_duration(iso_duration: Optional[str]) -> tuple[Optional[str], int]:
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


PREMIERE_TITLE_KWS = re.compile(r"\b(mv|official video|cover|premiere|trailer|teaser|lyric video)\b|翻唱|首播|原创|动画", re.IGNORECASE)
LIVE_TITLE_KWS = re.compile(r"\b(live|stream|chat|freechat)\b|🔴|直播|歌枠|杂谈|vtuber|耐久|アーカイブ", re.IGNORECASE)

PREMIERE_DESC_KWS = re.compile(r"\b(vocal|mix|illust|movie|director|music|arrangement)\s*[:：]", re.IGNORECASE)
LIVE_DESC_KWS = re.compile(r"\b(superchat|rules|streamlabs)\b|直播规则|聊天室规则|ルール", re.IGNORECASE)

def is_premiere_heuristic(item: dict, total_secs: int) -> bool:
    score = 0
    snippet = item.get("snippet", {})
    title = snippet.get("title", "")
    description = snippet.get("description", "")
    category_id = snippet.get("categoryId", "")

    if total_secs < YT_PREMIERE_SHORT:
        score += 80
    elif total_secs < YT_PREMIERE_MEDIUM:
        score += 40
    elif total_secs < YT_PREMIERE_LONG:
        score += 20
    elif total_secs > YT_LIVE_STRONG:
        score -= 80
    elif total_secs > YT_LIVE_THRESHOLD:
        score -= 40

    if PREMIERE_TITLE_KWS.search(title):
        score += 30
    if LIVE_TITLE_KWS.search(title):
        score -= 40

    if PREMIERE_DESC_KWS.search(description):
        score += 30
    if LIVE_DESC_KWS.search(description):
        score -= 40

    if category_id == "10":
        score += 20
    elif category_id == "20":
        score -= 15
    
    return score > PREMIERE_POSITIVE_THRESHOLD

def determine_video_status(item: dict, total_secs: int) -> str:
    """
    根据 YouTube API video item 精准判断视频状态。
    """
    snippet = item.get("snippet", {})
    live_content = snippet.get("liveBroadcastContent", "none") 
    live_details = item.get("liveStreamingDetails", {})

    if live_content == "live":
        return "live"
    if live_content == "upcoming":
        return "upcoming"

    if live_details.get("actualEndTime"):
        is_premiere = is_premiere_heuristic(item, total_secs)
        if is_premiere:
            return "upload"
        else:
            return "archive"

    if 0 < total_secs <= YT_SHORT_MAX_SECS:
        return "short"

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