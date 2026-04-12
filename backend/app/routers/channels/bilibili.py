from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session
from app.deps.platform_guard import PlatformContext, PlatformGuardDep
from app.models.models import Channel, Platform, User
from app.auth import get_current_user_optional
from app.integrations.bili_client import BiliClient, bili_client_dep
from app.services.bilibili_channel_service import _resolve_credential, fetch_bilibili_channel_data
from app.routers.channels.crud import _get_or_404

router = APIRouter()


@router.get("/{channel_id}/bilibili")
async def get_channel_bilibili_info(
    channel_id: int,
    dynamics_offset: str = Query(""),
    dynamics_limit: int = Query(12, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    ctx_platform: PlatformContext = PlatformGuardDep,
    current_user: Optional[User] = Depends(get_current_user_optional),
    client: BiliClient = Depends(bili_client_dep),
):
    channel = await _get_or_404(db, channel_id)
    ctx_platform.assert_bilibili_access()

    credential = _resolve_credential(current_user, client)
    data = await fetch_bilibili_channel_data(
        db, channel, credential, client, dynamics_offset, dynamics_limit
    )
    return {
        "info": data.info, "dynamics": data.dynamics,
        "videos": data.videos, "next_offset": data.next_offset,
    }