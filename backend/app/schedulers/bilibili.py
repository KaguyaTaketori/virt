from datetime import datetime, timezone

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.loguru_config import logger
from app.database_async import AsyncSessionFactory
from app.models.models import Channel, Platform, Stream
from app.services.bilibili_live import get_rooms_by_uids, parse_bilibili_room
from app.services.bilibili_video import sync_bilibili_channel_videos
from app.services.bilibili_profile import get_user_info_batch


async def _upsert_stream(
    db: AsyncSession, channel_id: int, parsed: dict, platform
) -> None:
    now = datetime.now(timezone.utc)

    insert_data = {
        "channel_id": channel_id,
        "platform": platform,
        "updated_at": now,
        **parsed,
    }

    dialect_name = db.bind.dialect.name
    insert_fn = pg_insert if dialect_name == "postgresql" else sqlite_insert

    stmt = insert_fn(Stream).values(**insert_data)

    update_cols = {
        "title": stmt.excluded.title,
        "status": stmt.excluded.status,
        "viewer_count": stmt.excluded.viewer_count,
        "updated_at": now,
    }

    update_cols["peak_viewers"] = func.max(
        Stream.peak_viewers, stmt.excluded.viewer_count
    )

    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=["channel_id", "video_id"], set_=update_cols
    )

    await db.execute(upsert_stmt)


async def _apply_user_info(channel: Channel, info: dict) -> bool:
    """将用户信息应用到 Channel 对象，返回是否有变更"""
    changed = False
    if info.get("name") and channel.name != info["name"]:
        channel.name = info["name"]
        changed = True
    if info.get("avatar_url") and channel.avatar_url != info["avatar_url"]:
        channel.avatar_url = info["avatar_url"]
        changed = True
    if info.get("fans") is not None:
        channel.bilibili_fans = info["fans"]
        changed = True
    if info.get("sign"):
        channel.bilibili_sign = info["sign"]
        changed = True
    if info.get("archive_count") is not None:
        channel.bilibili_archive_count = info["archive_count"]
        changed = True
    if info.get("avatar_url"):
        channel.bilibili_face = info["avatar_url"]
        changed = True
    if info.get("attention") is not None:
        channel.bilibili_following = info["attention"]
        changed = True
    if changed:
        channel.updated_at = datetime.now(timezone.utc)
    return changed


async def update_bilibili_streams():
    """更新 Bilibili 直播状态"""
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

    rooms_data = await get_rooms_by_uids(uids)

    async with AsyncSessionFactory() as db:
        for uid, room_data in rooms_data.items():
            if uid in uid_to_ch_id:
                parsed = parse_bilibili_room(room_data)
                await _upsert_stream(db, uid_to_ch_id[uid], parsed, Platform.BILIBILI)
        await db.commit()
        logger.info("更新 {} 个房间", len(rooms_data))


async def sync_bilibili_channels():
    """同步 Bilibili 频道信息（使用批量并发获取）"""
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

        # 批量并发获取用户信息
        uids = [ch.channel_id for ch in channels]
        async with httpx.AsyncClient(timeout=30.0) as client:
            user_infos = await get_user_info_batch(client, uids, max_concurrent=5)

        # 批量更新数据库
        uid_to_channel = {ch.channel_id: ch for ch in channels}
        for uid, info in user_infos.items():
            if not info:
                continue
            channel = uid_to_channel.get(uid)
            if not channel:
                continue

            changed = await _apply_user_info(channel, info)

            if changed:
                logger.info("更新频道信息: {}", channel.name)

        await db.commit()

        # 单独处理视频同步（每个频道独立事务）
        for ch in channels:
            total_synced = await sync_bilibili_channel_videos(db, ch.id, ch.channel_id)
            if total_synced > 0:
                logger.info("{}: 同步了 {} 个视频", ch.name, total_synced)

    logger.info("同步 {} 个频道信息", len(channels))
