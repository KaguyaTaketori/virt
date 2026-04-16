from __future__ import annotations

from app.database import session_scope, upsert_stream
from app.repositories import ChannelRepository
from app.models.models import Platform
from app.integrations.bili_client import get_bili_client
from app.loguru_config import logger


async def update_bilibili_streams() -> None:
    client = get_bili_client()
    async with session_scope() as session:
        channel_repo = ChannelRepository(session)
        channels = await channel_repo.get_active_channels(Platform.BILIBILI)
        if not channels:
            return
        uid_to_ch_id = {ch.channel_id: ch.id for ch in channels}
        uids = list(uid_to_ch_id.keys())

    rooms_data = await client.batch_get_live_status(uids)

    async with session_scope() as session:
        for uid, room_data in rooms_data.items():
            if uid in uid_to_ch_id and room_data and room_data.status != "offline":
                parsed = {
                    "video_id": room_data.video_id,
                    "title": room_data.title,
                    "thumbnail_url": room_data.thumbnail_url,
                    "status": room_data.status,
                    "viewer_count": room_data.viewer_count,
                    "started_at": room_data.started_at,
                }
                await upsert_stream(
                    session, uid_to_ch_id[uid], parsed, Platform.BILIBILI
                )
        await session.commit()
        logger.info("更新 {} 个房间", len(rooms_data))
