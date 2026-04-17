from fastapi import APIRouter

from app.deps.guards import AdminUser
from app.models.models import User
from app.deps import get_quota_dep
from app.worker.tasks.bilibili import update_bilibili_streams

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/trigger/bilibili-update")
async def trigger_bilibili_update(_: User = AdminUser):
    await update_bilibili_streams()
    return {"status": "ok", "message": "Bilibili stream update completed"}


@router.get("/quota")
async def get_quota_status(_: User = AdminUser):
    return await get_quota_dep().status()
