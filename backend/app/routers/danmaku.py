from fastapi import APIRouter, Depends
import httpx
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.danmaku import get_live_chat_messages
from app.services.danmaku_bilibili import get_bilibili_danmaku
from app.services.danmaku_youtube import (
    download_chat,
    get_chat_from_file,
    get_chat_from_db,
    save_to_db,
)
from app.config import settings

router = APIRouter(prefix="/api/danmaku", tags=["danmaku"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/youtube/file/{video_id}")
async def get_youtube_danmaku_from_file(video_id: str):
    """从本地文件获取YouTube弹幕"""
    if not settings.enable_danmaku:
        return {"messages": [], "enabled": False}

    messages = get_chat_from_file(video_id)
    return {"messages": messages, "enabled": True, "source": "file"}


@router.get("/youtube/db/{stream_id}")
async def get_youtube_danmaku_from_db(stream_id: int, db: Session = Depends(get_db)):
    """从数据库获取YouTube弹幕"""
    if not settings.enable_danmaku:
        return {"messages": [], "enabled": False}

    messages = get_chat_from_db(db, stream_id)
    return {"messages": messages, "enabled": True, "source": "db"}


@router.post("/youtube/download/{video_id}")
async def download_youtube_danmaku(
    video_id: str, stream_id: int = None, db: Session = Depends(get_db)
):
    """下载YouTube弹幕到文件和数据库"""
    if not settings.enable_danmaku:
        return {"success": False, "enabled": False}

    messages = download_chat(video_id)
    if not messages:
        return {"success": False, "error": "Failed to download chat"}

    result = {"success": True, "message_count": len(messages), "source": "file"}

    if stream_id:
        save_to_db(db, stream_id, video_id, messages)
        result["source"] = "db"
        result["saved_to_db"] = True

    return result


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
