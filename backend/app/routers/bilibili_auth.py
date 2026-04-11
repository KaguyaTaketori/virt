from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.permissions import has_permission
from app.services.bilibili_auth import bilibili_auth_service
from app.integrations import bilibili_service
from app.models.models import User
from app.auth import get_current_user_optional
from app.deps.base import get_db_session
from app.loguru_config import logger
from app.constants import PermissionAction, PermissionResource


router = APIRouter(prefix="/api/bilibili/auth", tags=["bilibili"])


async def get_current_active_user(
    current_user: User = Depends(get_current_user_optional),
) -> User:
    if current_user is None:
        raise HTTPException(status_code=401, detail="需要登录")
    return current_user


async def check_bilibili_permission(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
):
    has_perm = await has_permission(
        current_user.id, PermissionResource.BILIBILI, PermissionAction.ACCESS, db
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail="没有 B 站访问权限")
    return current_user


@router.post("/qrcode")
async def generate_qrcode(
    current_user: User = Depends(check_bilibili_permission),
):
    """
    生成 B 站登录二维码（需要 bilibili.access 权限）
    """
    result = await bilibili_auth_service.generate_qrcode()
    return result


@router.get("/qrcode/{session_id}")
async def check_qrcode_status(
    session_id: str,
    current_user: User = Depends(check_bilibili_permission),
    db: AsyncSession = Depends(get_db_session),
):
    """
    检查二维码登录状态，登录成功后自动保存凭证到用户账户
    """
    result = await bilibili_auth_service.check_status(session_id)

    if result.get("status") == "confirmed":
        credential = result.get("credential", {})
        await bilibili_service.save_user_credential(
            user_id=current_user.id,
            sessdata=credential.get("sessdata"),
            bili_jct=credential.get("bili_jct"),
            buvid3=credential.get("buvid3"),
            dedeuserid=credential.get("dedeuserid"),
            db=db,
        )
        logger.info("B站凭证已保存到用户账户, user_id={}", current_user.id)

    return result
