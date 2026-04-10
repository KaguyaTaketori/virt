from fastapi import APIRouter, Depends, Path as FPath
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.deps import get_db_session
from app.deps.platform_guard import PlatformContext, PlatformGuardDep
from app.services.danmaku import get_live_chat_messages
from app.services.danmaku_bilibili import get_bilibili_danmaku
from app.config import settings
from app.models.models import User
from app.services.permissions import get_user_roles
from app.auth import get_current_user
from app.services.api_key_manager import is_api_available
from app.constants import UserRole

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


async def require_registered_user(db: AsyncSession, current_user: Optional[User]):
    """要求注册用户及以上权限"""
    if not current_user:
        return False
    roles = await get_user_roles(current_user.id, db)
    return (
        UserRole.SUPERADMIN in roles
        or UserRole.ADMIN in roles
        or UserRole.OPERATOR in roles
        or UserRole.USER in roles
    )


@router.get("/youtube/file/{video_id}")
async def get_youtube_danmaku_from_file(
    video_id: str = FPath(..., pattern=r"^[a-zA-Z0-9_\-]{11}$"),
    _: User = Depends(get_current_user),
):
    if not settings.enable_danmaku:
        return {"messages": [], "enabled": False}
    messages = get_chat_from_file(video_id) if get_chat_from_file else []
    return {"messages": messages, "enabled": True, "source": "file"}


@router.get("/youtube/db/{stream_id}")
async def get_youtube_danmaku_from_db(
    stream_id: int,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    if not settings.enable_danmaku:
        return {"messages": [], "enabled": False}
    messages = await get_chat_from_db(db, stream_id) if get_chat_from_db else []
    return {"messages": messages, "enabled": True, "source": "db"}


@router.post("/youtube/download/{video_id}")
async def download_youtube_danmaku(
    video_id: str = FPath(..., pattern=r"^[a-zA-Z0-9_\-]{11}$"),
    stream_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    if not settings.enable_danmaku or not download_chat:
        return {"success": False, "enabled": False}
    messages = download_chat(video_id)
    if not messages:
        return {"success": False, "error": "Failed to download chat"}
    result = {"success": True, "message_count": len(messages), "source": "file"}
    if stream_id and save_to_db:
        await save_to_db(db, stream_id, video_id, messages)
        result.update(source="db", saved_to_db=True)
    return result


@router.get("/youtube/{live_chat_id}")
async def get_youtube_danmaku(live_chat_id: str, page_token: Optional[str] = None):
    if not settings.enable_danmaku:
        return {"messages": [], "enabled": False}
    if not await is_api_available():
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
    ctx: PlatformContext = PlatformGuardDep,
):
    ctx.assert_bilibili_access()

    if not settings.enable_danmaku:
        return {"messages": [], "enabled": False}
    messages = await get_bilibili_danmaku(room_id)
    return {"messages": messages, "enabled": True}
