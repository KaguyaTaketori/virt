from fastapi import APIRouter

from app.deps.permissions import AdminUser
from app.models.models import User
from app.scheduler_tasks import (
    discover_youtube_streams,
    update_bilibili_streams,
    sync_bilibili_channels,
)
from app.services.quota_guard import status as quota_status

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/trigger/youtube-discover")
async def trigger_youtube_discover(_: User = AdminUser):
    await discover_youtube_streams()
    return {"status": "ok", "message": "YouTube discover job completed"}


@router.post("/trigger/bilibili-update")
async def trigger_bilibili_update(_: User = AdminUser):
    await update_bilibili_streams()
    return {"status": "ok", "message": "Bilibili stream update completed"}


@router.post("/trigger/bilibili-sync-channels")
async def trigger_bilibili_sync_channels(_: User = AdminUser):
    await sync_bilibili_channels()
    return {"status": "ok", "message": "Bilibili channel sync completed"}


@router.get("/quota")
def get_quota_status(
    _: User = AdminUser
):
    return quota_status()