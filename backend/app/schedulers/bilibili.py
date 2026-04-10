from __future__ import annotations

from sqlalchemy import select

from app.loguru_config import logger
from app.database_async import AsyncSessionFactory
from app.models.models import Channel, Platform
from app.services.bilibili_live import get_rooms_by_uids, parse_bilibili_room
from app.db_utils import upsert_stream
from app.crud.session import session_scope
from app.crud import ChannelRepository


async def update_bilibili_streams():
    """更新 Bilibili 直播状态。"""
    async with session_scope() as session:
        channel_repo = ChannelRepository(session)
        channels = await channel_repo.get_active_channels(Platform.BILIBILI)

        if not channels:
            return

        uid_to_ch_id = {ch.channel_id: ch.id for ch in channels}
        uids = list(uid_to_ch_id.keys())

    rooms_data = await get_rooms_by_uids(uids)

    async with session_scope() as session:
        for uid, room_data in rooms_data.items():
            if uid in uid_to_ch_id:
                parsed = parse_bilibili_room(room_data)
                await upsert_stream(
                    session, uid_to_ch_id[uid], parsed, Platform.BILIBILI
                )

        await session.commit()
        logger.info("更新 %d 个房间", len(rooms_data))
