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
