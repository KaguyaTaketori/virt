from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session
from app.deps.platform_guard import PlatformContext, PlatformGuardDep
from app.models.models import Channel, Platform, User
from app.auth import get_current_user_optional
from app.integrations.bili_client import BiliClient, bili_client_dep

router = APIRouter()


@router.get("/{channel_id}/bilibili")
async def get_channel_bilibili_info(
    channel_id: int,
    dynamics_offset: str = Query("", ge=""),
    dynamics_limit: int = Query(12, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    ctx_platform: PlatformContext = PlatformGuardDep,
    current_user: User = Depends(get_current_user_optional),
    client: BiliClient = Depends(bili_client_dep),
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if channel.platform != Platform.BILIBILI:
        raise HTTPException(status_code=400, detail="Channel is not a Bilibili channel")

    ctx_platform.assert_bilibili_access()

    uid = channel.channel_id

    credential = None
    if current_user and current_user.bilibili_sessdata:
        try:
            from bilibili_api import Credential

            credential = Credential(
                sessdata=current_user.bilibili_sessdata,
                bili_jct=current_user.bilibili_bili_jct,
                buvid3=current_user.bilibili_buvid3,
            )
        except Exception:
            pass

    if not credential and client._create_credential():
        credential = client._create_credential()

    videos = []
    try:
        videos_raw = await client.get_videos(uid, credential, page=1, page_size=30)
        vlist = videos_raw.get("list", {}).get("vlist", [])
        videos = [client._parse_video(v) for v in vlist]
    except Exception:
        pass

    dynamics, next_offset = [], ""
    if credential:
        dynamics, next_offset = await client.get_dynamics(
            uid, credential, offset=dynamics_offset
        )
        if dynamics:
            await client.upsert_dynamics(db, channel_id, dynamics, [])

    if not dynamics:
        from app.models.models import BilibiliDynamic

        result = await db.execute(
            select(BilibiliDynamic)
            .where(BilibiliDynamic.channel_id == channel_id)
            .order_by(BilibiliDynamic.timestamp.desc())
            .limit(dynamics_limit)
        )
        dynamics = []
        for row in result.scalars().all():
            dynamics.append(
                {
                    "dynamic_id": row.dynamic_id,
                    "uid": row.uid,
                    "uname": row.uname,
                    "content_nodes": row.content_nodes,
                    "images": row.images,
                    "timestamp": row.timestamp,
                    "url": row.url,
                }
            )

    info_data = await client.get_channel_info(uid, credential)
    if info_data:
        if info_data.get("name"):
            channel.name = info_data["name"]
        if info_data.get("face"):
            channel.bilibili_face = info_data["face"]
        if info_data.get("sign"):
            channel.bilibili_sign = info_data["sign"]
        if info_data.get("fans"):
            channel.bilibili_fans = info_data["fans"]
        if info_data.get("archive_count"):
            channel.bilibili_archive_count = info_data["archive_count"]
        await db.commit()

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
