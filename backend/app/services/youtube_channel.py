import httpx
from app.config import settings


YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


async def get_youtube_channel_info(channel_id: str) -> dict | None:
    """通过 YouTube Data API 获取频道信息"""
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
            }
    except Exception as e:
        print(f"Failed to get YouTube channel info for {channel_id}: {e}")
        return None
