# backend/app/routers/admin.py
from fastapi import APIRouter, Depends, HTTPException, Header
from app.scheduler_tasks import (
    discover_youtube_streams,
    update_bilibili_streams,
    sync_bilibili_channels,
)
from app.services.quota_guard import status as quota_status
from app.config import settings

router = APIRouter(prefix="/api/admin", tags=["admin"])


def verify_admin_key(x_admin_key: str = Header(default=None)):
    """
    简单的静态 API Key 验证。
    .env 里没有配置 admin_secret_key 时跳过验证（方便本地开发）。
    生产环境必须在 .env 里设置，否则任何人都能触发 job。
    """
    if not settings.admin_secret_key:
        return  # 未配置，开发模式放行
    if x_admin_key != settings.admin_secret_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing X-Admin-Key header"
        )


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


@router.get("/quota")  # quota 查询不需要鉴权，只是只读状态
def get_quota_status():
    return quota_status()