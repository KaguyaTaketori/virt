import httpx
from app.config import settings
from app.services.api_key_manager import get_api_key, is_api_available

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


async def get_live_chat_messages(
    client: httpx.AsyncClient,
    live_chat_id: str,
    page_token: str = None,
) -> dict:
    """获取YouTube直播聊天消息"""
    if not await is_api_available():
        return {"messages": [], "next_page_token": None}

    api_key = await get_api_key()
    if not api_key:
        return {"messages": [], "next_page_token": None}

    params = {
        "key": api_key,
        "liveChatId": live_chat_id,
        "part": "snippet,authorDetails",
        "maxResults": 50,
    }
    if page_token:
        params["pageToken"] = page_token

    resp = await client.get(f"{YOUTUBE_API_BASE}/liveChatMessages", params=params)
    resp.raise_for_status()
    data = resp.json()

    messages = []
    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        author = item.get("authorDetails", {})
        if snippet.get("type") == "textMessageEvent":
            messages.append(
                {
                    "author": author.get("displayName", ""),
                    "message": snippet.get("textMessageDetails", {}).get(
                        "messageText", ""
                    ),
                    "timestamp": snippet.get("publishedAt"),
                }
            )

    return {
        "messages": messages,
        "next_page_token": data.get("nextPageToken"),
    }
