from fastapi import APIRouter, Depends

from app.deps import verify_admin_key
from app.scheduler_tasks import (
    discover_youtube_streams,
    update_bilibili_streams,
    sync_bilibili_channels,
)
from app.services.quota_guard import status as quota_status

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/trigger/youtube-discover", dependencies=[Depends(verify_admin_key)])
async def trigger_youtube_discover():
    await discover_youtube_streams()
    return {"status": "ok", "message": "YouTube discover job completed"}


@router.post("/trigger/bilibili-update", dependencies=[Depends(verify_admin_key)])
async def trigger_bilibili_update():
    await update_bilibili_streams()
    return {"status": "ok", "message": "Bilibili stream update completed"}


@router.post("/trigger/bilibili-sync-channels", dependencies=[Depends(verify_admin_key)])
async def trigger_bilibili_sync_channels():
    await sync_bilibili_channels()
    return {"status": "ok", "message": "Bilibili channel sync completed"}


@router.get("/quota")
def get_quota_status():
    return quota_status()