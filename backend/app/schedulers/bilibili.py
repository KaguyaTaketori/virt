
from sqlalchemy import select

from app.loguru_config import logger
from app.database_async import AsyncSessionFactory
from app.models.models import Channel, Platform
from app.services.bilibili_live import get_rooms_by_uids, parse_bilibili_room
from app.db_utils import upsert_stream


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
                await upsert_stream(db, uid_to_ch_id[uid], parsed, Platform.BILIBILI)
        await db.commit()
        logger.info("更新 {} 个房间", len(rooms_data))
