from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.loguru_config import logger
from app.database_async import AsyncSessionFactory
from app.models.models import Channel, Platform, Stream
from app.services.bilibili_fetcher import get_rooms_by_uids, get_user_info, parse_bilibili_room, sync_bilibili_channel_videos


async def _async_upsert_stream(
    db: AsyncSession, channel_id: int, parsed: dict, platform
):
    result = await db.execute(
        select(Stream).where(
            Stream.channel_id == channel_id,
            Stream.video_id == parsed["video_id"],
        )
    )
    stream = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if not stream:
        stream = Stream(channel_id=channel_id, platform=platform)
        db.add(stream)

    for field, value in parsed.items():
        if getattr(stream, field, None) != value:
            setattr(stream, field, value)

    stream.updated_at = now
    if parsed.get("viewer_count", 0) > (stream.peak_viewers or 0):
        stream.peak_viewers = parsed["viewer_count"]


async def update_bilibili_streams():
    """使用 AsyncSession，与 YouTube 任务保持一致。"""
    async with AsyncSessionFactory() as db:
        result = await db.execute(
            select(Channel).where(
                Channel.platform == Platform.BILIBILI,
                Channel.is_active.is_(True),
            )
        )
        channels = result.scalars().all()
        if not channels:
            return

        uid_to_ch_id = {ch.channel_id: ch.id for ch in channels}
        uids = list(uid_to_ch_id.keys())

    async with httpx.AsyncClient(timeout=30.0) as client:
        rooms_data = await get_rooms_by_uids(client, uids)

    async with AsyncSessionFactory() as db:
        for uid, room_data in rooms_data.items():
            if uid in uid_to_ch_id:
                parsed = parse_bilibili_room(room_data)
                await _async_upsert_stream(
                    db, uid_to_ch_id[uid], parsed, Platform.BILIBILI
                )
        await db.commit()
        logger.info("更新 {} 个房间", len(rooms_data))


async def sync_bilibili_channels():
    async with AsyncSessionFactory() as db:
        result = await db.execute(
            select(Channel).where(
                Channel.platform == Platform.BILIBILI,
                Channel.is_active == True,
            )
        )
        channels = result.scalars().all()
        if not channels:
            return

        async with httpx.AsyncClient(timeout=30.0) as client:
            for ch in channels:
                info = await get_user_info(client, ch.channel_id)
                if not info:
                    continue
                changed = False
                if info.get("name") and ch.name != info["name"]:
                    ch.name = info["name"]
                    changed = True
                if info.get("avatar_url") and ch.avatar_url != info["avatar_url"]:
                    ch.avatar_url = info["avatar_url"]
                    changed = True

                if info.get("fans") is not None:
                    ch.bilibili_fans = info["fans"]
                    changed = True
                if info.get("sign"):
                    ch.bilibili_sign = info["sign"]
                    changed = True
                if info.get("archive_count") is not None:
                    ch.bilibili_archive_count = info["archive_count"]
                    changed = True
                if info.get("avatar_url"):
                    ch.bilibili_face = info["avatar_url"]
                    changed = True
                if info.get("attention") is not None:
                    ch.bilibili_following = info["attention"]
                    changed = True

                if changed:
                    ch.updated_at = datetime.now(timezone.utc)

                total_synced = await sync_bilibili_channel_videos(
                    db, ch.id, ch.channel_id
                )
                if total_synced > 0:
                    logger.info("{}: 同步了 {} 个视频", ch.name, total_synced)

        await db.commit()
        logger.info("同步 {} 个频道信息", len(channels))
