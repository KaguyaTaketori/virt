from fastapi import APIRouter
from app.scheduler_tasks import (
    discover_youtube_streams,
    update_bilibili_streams,
    sync_bilibili_channels,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/trigger/youtube-discover")
async def trigger_youtube_discover():
    await discover_youtube_streams()
    return {"status": "ok", "message": "YouTube discover job completed"}


@router.post("/trigger/bilibili-update")
async def trigger_bilibili_update():
    await update_bilibili_streams()
    return {"status": "ok", "message": "Bilibili stream update completed"}


@router.post("/trigger/bilibili-sync-channels")
async def trigger_bilibili_sync_channels():
    """同步 B站频道头像和名字，调试用。"""
    await sync_bilibili_channels()
    return {"status": "ok", "message": "Bilibili channel sync completed"}
