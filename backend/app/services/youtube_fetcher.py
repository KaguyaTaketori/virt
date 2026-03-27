import httpx
import asyncio
from datetime import datetime, timezone
from typing import Optional
from app.config import settings

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def _parse_yt_datetime(s: Optional[str]) -> Optional[datetime]:
    """把 YouTube 返回的 ISO 8601 字符串转成 aware datetime。"""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


async def get_channel_live_video_ids(
    client: httpx.AsyncClient,
    channel_id: str,
) -> list[str]:
    """
    用 search.list 查频道当前的 live/upcoming videoId。
    消耗 100 配额/次，只在发现 job 里调用。
    """
    resp = await client.get(
        f"{YOUTUBE_API_BASE}/search",
        params={
            "key": settings.youtube_api_key,
            "channelId": channel_id,
            "part": "id",
            "eventType": "live",
            "type": "video",
            "maxResults": 5,
        },
        timeout=15.0,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return [item["id"]["videoId"] for item in items]


async def get_channel_upcoming_video_ids(
    client: httpx.AsyncClient,
    channel_id: str,
) -> list[str]:
    """查 upcoming（预告）流，和 live 分开调用节省配额。"""
    resp = await client.get(
        f"{YOUTUBE_API_BASE}/search",
        params={
            "key": settings.youtube_api_key,
            "channelId": channel_id,
            "part": "id",
            "eventType": "upcoming",
            "type": "video",
            "maxResults": 5,
        },
        timeout=15.0,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return [item["id"]["videoId"] for item in items]


async def get_videos_details(
    client: httpx.AsyncClient,
    video_ids: list[str],
) -> list[dict]:
    """
    批量拉视频详情，1 配额可查 50 个。
    这是轮询 job 的主力函数。
    """
    if not video_ids:
        return []

    all_items = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        resp = await client.get(
            f"{YOUTUBE_API_BASE}/videos",
            params={
                "key": settings.youtube_api_key,
                "id": ",".join(chunk),
                "part": "snippet,liveStreamingDetails,statistics",
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        all_items.extend(resp.json().get("items", []))

    return all_items


def parse_youtube_stream(item: dict) -> Optional[dict]:
    """
    把 YouTube API 的 video item 解析成统一内部格式。
    返回 None 表示该视频不是直播相关内容，可以忽略。
    """
    snippet = item.get("snippet", {})
    live_details = item.get("liveStreamingDetails", {})
    life_cycle = snippet.get("liveBroadcastContent", "none")

    if life_cycle == "none" and not live_details.get("actualStartTime"):
        return None

    status_map = {
        "live": "live",
        "upcoming": "upcoming",
        "none": "archive",
    }

    concurrent = live_details.get("concurrentViewers")
    viewer_count = int(concurrent) if concurrent and concurrent.isdigit() else 0

    # 缩略图优先级：maxres > high > medium > default
    thumbnails = snippet.get("thumbnails", {})
    thumbnail_url = (
        thumbnails.get("maxres", {}).get("url")
        or thumbnails.get("high", {}).get("url")
        or thumbnails.get("medium", {}).get("url")
        or thumbnails.get("default", {}).get("url")
    )

    return {
        "video_id": item["id"],
        "title": snippet.get("title"),
        "thumbnail_url": thumbnail_url,
        "status": status_map.get(life_cycle, "archive"),
        "viewer_count": viewer_count,
        "scheduled_at": _parse_yt_datetime(live_details.get("scheduledStartTime")),
        "started_at": _parse_yt_datetime(live_details.get("actualStartTime")),
        "ended_at": _parse_yt_datetime(live_details.get("actualEndTime")),
        "live_chat_id": live_details.get("activeLiveChatId"),
    }
