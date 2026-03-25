import httpx
import asyncio
from datetime import datetime, timezone
from typing import Optional
from app.config import settings  # YOUTUBE_API_KEY

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


async def get_channel_live_video_ids(
    client: httpx.AsyncClient,
    channel_id: str,
) -> list[str]:
    """
    Step 1: 获取频道当前 live/upcoming 的 videoId 列表
    注意：search.list 消耗 100 配额，但这是唯一能按 eventType 过滤的方式
    策略：对活跃频道每 5 分钟查一次，降低总配额消耗
    """
    resp = await client.get(f"{YOUTUBE_API_BASE}/search", params={
        "key": settings.youtube_api_key,
        "channelId": channel_id,
        "part": "id",
        "eventType": "live",      # 也可以是 "upcoming"
        "type": "video",
        "maxResults": 5,
    })
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return [item["id"]["videoId"] for item in items]


async def get_videos_details(
    client: httpx.AsyncClient,
    video_ids: list[str],
) -> list[dict]:
    """
    Step 2: 批量获取视频详情（1 配额可查 50 个）
    这是主力函数，每分钟轮询已知 videoId 的实时观看人数
    """
    if not video_ids:
        return []
    
    # YouTube API 单次最多 50 个 id
    chunks = [video_ids[i:i+50] for i in range(0, len(video_ids), 50)]
    all_items = []
    
    for chunk in chunks:
        resp = await client.get(f"{YOUTUBE_API_BASE}/videos", params={
            "key": settings.youtube_api_key,
            "id": ",".join(chunk),
            "part": "snippet,liveStreamingDetails,statistics",
        })
        resp.raise_for_status()
        all_items.extend(resp.json().get("items", []))
    
    return all_items


def parse_youtube_stream(item: dict) -> Optional[dict]:
    """将 YouTube API 响应解析为统一的内部格式"""
    snippet = item.get("snippet", {})
    live_details = item.get("liveStreamingDetails", {})
    
    # 判断状态
    broadcast_status = live_details.get("activeLiveChatId")
    life_cycle = snippet.get("liveBroadcastContent")  # "live" | "upcoming" | "none"
    
    status_map = {
        "live": "live",
        "upcoming": "upcoming",
        "none": "archive",  # 已结束变为录播
    }
    
    concurrent_viewers = live_details.get("concurrentViewers")
    
    return {
        "video_id": item["id"],
        "title": snippet.get("title"),
        "thumbnail_url": (
            snippet.get("thumbnails", {})
            .get("maxres", snippet.get("thumbnails", {}).get("high", {}))
            .get("url")
        ),
        "status": status_map.get(life_cycle, "offline"),
        "viewer_count": int(concurrent_viewers) if concurrent_viewers else 0,
        "scheduled_at": live_details.get("scheduledStartTime"),
        "started_at": live_details.get("actualStartTime"),
        "ended_at": live_details.get("actualEndTime"),
    }