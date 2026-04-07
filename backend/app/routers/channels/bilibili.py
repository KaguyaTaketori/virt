"""
backend/app/routers/channels/bilibili.py
B 站频道详情接口（修复问题 7：补齐视频列表返回）。
"""

from __future__ import annotations

import asyncio
from fastapi import APIRouter, Depends, HTTPException
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
    db: AsyncSession = Depends(get_db_session),
    ctx: PlatformContext = PlatformGuardDep,
    current_user: User = Depends(get_current_user_optional),
):
    """
    返回 B 站频道信息、动态列表、视频列表。
    修复：原实现只返回动态，videos 字段始终为空，导致前端「投稿」Tab 永远空白。
    """
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if channel.platform != Platform.BILIBILI:
        raise HTTPException(status_code=400, detail="Channel is not a Bilibili channel")

    ctx.assert_bilibili_access()

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

    dynamics_task = asyncio.create_task(bilibili_channel_service.get_dynamics(uid))
    videos_task = asyncio.create_task(bilibili_channel_service.get_videos(uid))
    dynamics, videos = await asyncio.gather(dynamics_task, videos_task)

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
    }
