import re
import subprocess
import httpx
from app.config import settings


YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def resolve_youtube_channel(input_str: str) -> str | None:
    """解析各种YouTube频道格式，返回channel_id"""
    if not input_str:
        return None

    if input_str.startswith("UC") and len(input_str) >= 22:
        return input_str

    try:
        result = subprocess.run(
            ["yt-dlp", "--print", "channel_id", input_str],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception as e:
        print(f"Failed to resolve channel: {e}")

    return None


async def get_youtube_channel_info(input_str: str) -> dict | None:
    """通过 YouTube Data API 获取频道信息"""
    channel_id = resolve_youtube_channel(input_str)
    if not channel_id:
        return None

    if not settings.youtube_api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{YOUTUBE_API_BASE}/channels",
                params={
                    "part": "snippet",
                    "id": channel_id,
                    "key": settings.youtube_api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            items = data.get("items", [])
            if not items:
                return None

            snippet = items[0].get("snippet", {})
            thumbnails = snippet.get("thumbnails", {})

            return {
                "title": snippet.get("title"),
                "avatar_url": thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url"),
                "channel_id": channel_id,
            }
    except Exception as e:
        print(f"Failed to get YouTube channel info for {channel_id}: {e}")
        return None
