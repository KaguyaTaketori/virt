from fastapi import APIRouter
import httpx
from app.services.danmaku import get_live_chat_messages
from app.services.danmaku_bilibili import get_bilibili_danmaku
from app.config import settings

router = APIRouter(prefix="/api/danmaku", tags=["danmaku"])


@router.get("/youtube/{live_chat_id}")
async def get_youtube_danmaku(live_chat_id: str, page_token: str = None):
    """
    获取YouTube直播弹幕/聊天消息
    需要传入 live_chat_id（从 streams 表获取）
    """
    if not settings.enable_danmaku:
        return {"messages": [], "enabled": False}

    if not settings.youtube_api_key:
        return {"messages": [], "error": "YouTube API key not configured"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        result = await get_live_chat_messages(client, live_chat_id, page_token)
        return {
            "messages": result["messages"],
            "next_page_token": result["next_page_token"],
            "enabled": True,
        }


@router.get("/bilibili/{room_id}")
async def get_bilibili_danmaku_endpoint(room_id: str):
    """获取B站直播弹幕"""
    if not settings.enable_danmaku:
        return {"messages": [], "enabled": False}

    messages = await get_bilibili_danmaku(room_id)
    return {"messages": messages, "enabled": True}
