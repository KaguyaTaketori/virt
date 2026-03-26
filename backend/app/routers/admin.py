# backend/app/routers/admin.py  ← 新建文件
from fastapi import APIRouter
from app.scheduler_tasks import discover_youtube_streams, update_bilibili_streams

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/trigger/youtube-discover")
async def trigger_youtube_discover():
    """手动触发 YouTube 发现 job，无需等待定时器。调试用。"""
    await discover_youtube_streams()
    return {"status": "ok", "message": "YouTube discover job completed"}


@router.post("/trigger/bilibili-update")
async def trigger_bilibili_update():
    """手动触发 Bilibili 更新 job。"""
    await update_bilibili_streams()
    return {"status": "ok", "message": "Bilibili update job completed"}