from fastapi import APIRouter, Depends
import httpx
from sqlalchemy.orm import Session
from typing import Optional
from app.database import SessionLocal
from app.services.danmaku import get_live_chat_messages
from app.services.danmaku_bilibili import get_bilibili_danmaku
from app.config import settings
from app.models.models import User
from app.services.permissions import get_user_roles, has_permission
from app.auth import get_current_user_optional
from fastapi import HTTPException
from app.deps import get_db

try:
    from app.services.danmaku_youtube import (
        download_chat,
        get_chat_from_file,
        get_chat_from_db,
        save_to_db,
    )

    DANMAKU_YT_AVAILABLE = True
except ImportError:
    DANMAKU_YT_AVAILABLE = False
    download_chat = None
    get_chat_from_file = None
    get_chat_from_db = None
    save_to_db = None

router = APIRouter(prefix="/api/danmaku", tags=["danmaku"])

def require_registered_user(db: Session, current_user: Optional[User]):
    """要求注册用户及以上权限"""
    if not current_user:
        return False
    roles = get_user_roles(current_user.id, db)
    return (
        "superadmin" in roles
        or "admin" in roles
        or "operator" in roles
        or "user" in roles
    )


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
async def get_bilibili_danmaku_endpoint(
    room_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """获取B站直播弹幕 - 需要bilibili.access权限"""
    if current_user and has_permission(current_user.id, "bilibili", "access", db):
        pass
    elif current_user:
        roles = get_user_roles(current_user.id, db)
        if (
            "operator" not in roles
            and "admin" not in roles
            and "superadmin" not in roles
        ):
            raise HTTPException(status_code=403, detail="需要B站访问权限")
    else:
        raise HTTPException(status_code=401, detail="请先登录")

    if not settings.enable_danmaku:
        return {"messages": [], "enabled": False}

    messages = await get_bilibili_danmaku(room_id)
    return {"messages": messages, "enabled": True}
