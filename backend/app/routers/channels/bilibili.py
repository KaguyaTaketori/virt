"""
backend/app/routers/channels/bilibili.py
B 站频道详情接口 - 支持实时获取 + 数据库 fallback
"""

from __future__ import annotations

import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session
from app.deps.platform_guard import PlatformContext, PlatformGuardDep
from app.models.models import Channel, Platform, User
from app.auth import get_current_user_optional
from app.services.bilibili_channel import bilibili_channel_service
from app.services.bilibili_user import bilibili_user_service

router = APIRouter()


@router.get("/{channel_id}/bilibili")
async def get_channel_bilibili_info(
    channel_id: int,
    dynamics_offset: str = Query("", ge=""),
    dynamics_limit: int = Query(12, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    ctx: PlatformContext = PlatformGuardDep,
    current_user: User = Depends(get_current_user_optional),
):
    """
    返回 B 站频道信息、动态列表、视频列表。
    - 动态和视频优先实时获取，失败时 fallback 到数据库
    - 动态支持分页 (offset, limit)
    """
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if channel.platform != Platform.BILIBILI:
        raise HTTPException(status_code=400, detail="Channel is not a Bilibili channel")

    ctx.assert_bilibili_access()

    # 设置数据库上下文
    bilibili_channel_service.set_db_context(db, channel_id)

    # 尝试使用用户凭证
    if current_user:
        user_cred = await bilibili_user_service.get_credential(current_user.id, db)
        if user_cred:
            bilibili_channel_service.set_user_credential(
                sessdata=user_cred["sessdata"],
                bili_jct=user_cred["bili_jct"],
                buvid3=user_cred["buvid3"],
                dedeuserid=user_cred.get("dedeuserid"),
            )

    uid = channel.channel_id

    # 实时获取所有视频，失败则从数据库读取
    videos = await bilibili_channel_service.get_all_videos(uid)
    if not videos:
        videos = await bilibili_channel_service.get_videos_from_db(channel_id)

    # 实时获取动态，失败则从数据库读取
    dynamics, next_offset = await bilibili_channel_service.get_dynamics(
        uid, offset=dynamics_offset, limit=100
    )
    if not dynamics:
        dynamics = await bilibili_channel_service.get_dynamics_from_db(
            channel_id, offset=0, limit=dynamics_limit
        )
        next_offset = ""

    info = {
        "mid": uid,
        "name": channel.name,
        "face": channel.bilibili_face,
        "sign": channel.bilibili_sign,
        "fans": channel.bilibili_fans,
        "attention": channel.bilibili_following,
        "archive_count": channel.bilibili_archive_count,
    }

    return {
        "info": info,
        "dynamics": dynamics or [],
        "videos": videos or [],
        "next_offset": next_offset,
    }
