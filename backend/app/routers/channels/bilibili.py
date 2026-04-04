"""
backend/app/routers/channels/bilibili.py
B 站频道详情接口（修复问题 7：补齐视频列表返回）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_async_db
from app.deps.platform_guard import PlatformContext, PlatformGuardDep
from app.models.models import Channel, Platform
from app.services.bilibili_channel import bilibili_channel_service

router = APIRouter()


@router.get("/{channel_id}/bilibili")
async def get_channel_bilibili_info(
    channel_id: int,
    db: AsyncSession = Depends(get_async_db),
    ctx: PlatformContext = PlatformGuardDep,
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

    # 权限检查：未登录或无 bilibili.access 权限时 403
    ctx.assert_bilibili_access()

    uid = channel.channel_id

    # 并发拉取动态与视频，减少等待时间
    import asyncio
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
        "videos": videos or [],  # ← 修复：原来此处硬编码返回 []
    }