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
from app.services.bilibili_channel_service import (
    _resolve_credential,
    fetch_bilibili_channel_data,
    fetch_bilibili_info,
    fetch_bilibili_videos,
    fetch_bilibili_dynamics,
)
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
        "info": data.info,
        "dynamics": data.dynamics,
        "videos": data.videos,
        "next_offset": data.next_offset,
    }


@router.get("/{channel_id}/bilibili/info")
async def get_channel_bilibili_info_only(
    channel_id: int,
    db: AsyncSession = Depends(get_db_session),
    ctx_platform: PlatformContext = PlatformGuardDep,
    current_user: Optional[User] = Depends(get_current_user_optional),
    client: BiliClient = Depends(bili_client_dep),
):
    channel = await _get_or_404(db, channel_id)
    ctx_platform.assert_bilibili_access()

    credential = _resolve_credential(current_user, client)
    data = await fetch_bilibili_info(db, channel, credential, client)
    return {
        "mid": data.mid,
        "name": data.name,
        "face": data.face,
        "sign": data.sign,
        "fans": data.fans,
        "attention": data.attention,
        "archive_count": data.archive_count,
    }


@router.get("/{channel_id}/bilibili/videos")
async def get_channel_bilibili_videos_only(
    channel_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    ctx_platform: PlatformContext = PlatformGuardDep,
    current_user: Optional[User] = Depends(get_current_user_optional),
    client: BiliClient = Depends(bili_client_dep),
):
    channel = await _get_or_404(db, channel_id)
    ctx_platform.assert_bilibili_access()

    credential = _resolve_credential(current_user, client)
    data = await fetch_bilibili_videos(db, channel, credential, client, page, page_size)
    return {
        "videos": [
            {
                "bvid": v.bvid,
                "title": v.title,
                "pic": v.pic,
                "duration": v.duration,
                "pubdate": v.pubdate,
                "play": v.play,
            }
            for v in data.videos
        ],
        "total": data.total,
    }


@router.get("/{channel_id}/bilibili/dynamics")
async def get_channel_bilibili_dynamics_only(
    channel_id: int,
    offset: str = Query(""),
    limit: int = Query(12, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    ctx_platform: PlatformContext = PlatformGuardDep,
    current_user: Optional[User] = Depends(get_current_user_optional),
    client: BiliClient = Depends(bili_client_dep),
):
    channel = await _get_or_404(db, channel_id)
    ctx_platform.assert_bilibili_access()

    credential = _resolve_credential(current_user, client)
    data = await fetch_bilibili_dynamics(db, channel, credential, client, offset, limit)
    return {
        "dynamics": data.dynamics,
        "next_offset": data.next_offset,
    }
