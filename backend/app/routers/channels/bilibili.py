"""
backend/app/routers/channels/bilibili.py
B 站频道详情接口 - 支持实时获取 + 数据库 fallback
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session
from app.deps.platform_guard import PlatformContext, PlatformGuardDep
from app.models.models import Channel, Platform, User
from app.auth import get_current_user_optional
from app.services.bilibili_channel import bilibili_channel_service
from app.services.bilibili_user import bilibili_user_service
from app.services.bilibili_context import ChannelRequestContext

router = APIRouter()


@router.get("/{channel_id}/bilibili")
async def get_channel_bilibili_info(
    channel_id: int,
    dynamics_offset: str = Query("", ge=""),
    dynamics_limit: int = Query(12, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    ctx_platform: PlatformContext = PlatformGuardDep,
    current_user: User = Depends(get_current_user_optional),
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if channel.platform != Platform.BILIBILI:
        raise HTTPException(status_code=400, detail="Channel is not a Bilibili channel")

    ctx_platform.assert_bilibili_access()

    ctx = await ChannelRequestContext.build(
        db=db,
        channel_id=channel_id,
        current_user=current_user,
        bilibili_user_service=bilibili_user_service,
    )

    uid = channel.channel_id

    # 实时获取所有视频，失败则从数据库读取
    videos = await bilibili_channel_service.get_all_videos(uid, ctx)
    if not videos:
        videos = await bilibili_channel_service.get_videos_from_db(channel_id, db)

    # 实时获取动态，失败则从数据库读取
    dynamics, next_offset = await bilibili_channel_service.get_dynamics(
        uid, ctx, offset=dynamics_offset
    )
    if not dynamics:
        dynamics = await bilibili_channel_service.get_dynamics_from_db(
            channel_id, db, offset=0, limit=dynamics_limit
        )
        next_offset = ""

    # 实时获取并更新频道信息
    info_data = await bilibili_channel_service.get_info(uid, ctx)
    if info_data:
        await bilibili_channel_service.update_channel(channel, info_data, db)

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
