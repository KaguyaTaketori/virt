from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models.models import Channel, Platform, UserChannel, Video, Stream, Danmaku
from app.schemas.schemas import ChannelCreate
from app.services.youtube_channel import get_channel_details, get_youtube_channel_info

class ChannelService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_404(self, channel_id: int) -> Channel:
        result = await self.db.execute(select(Channel).where(Channel.id == channel_id))
        channel = result.scalar_one_or_none()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        return channel

    async def prepare_youtube_data(self, channel_in: ChannelCreate) -> dict:
        resolved_id = channel_in.channel_id
        data = channel_in.model_dump()
        
        info = await get_youtube_channel_info(channel_in.channel_id)
        if info and info.get("channel_id"):
            resolved_id = info["channel_id"]
            data["channel_id"] = resolved_id
            data["avatar_url"] = data.get("avatar_url") or info.get("avatar_url")
            data["name"] = data.get("name") or info.get("title")

        details = await get_channel_details(resolved_id)
        if details:
            fields = ("banner_url", "description", "twitter_url", "youtube_url")
            for field in fields:
                if not data.get(field) and details.get(field):
                    data[field] = details[field]
        
        return data

    async def create_channel(self, channel_in: ChannelCreate) -> Channel:
        if channel_in.platform == Platform.YOUTUBE:
            processed_data = await self.prepare_youtube_data(channel_in)
        else:
            processed_data = channel_in.model_dump()

        existing = await self.db.execute(
            select(Channel).where(Channel.channel_id == processed_data["channel_id"])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Channel already exists")

        db_channel = Channel(**processed_data)
        self.db.add(db_channel)
        await self.db.commit()
        await self.db.refresh(db_channel)
        return db_channel

    async def delete_channel_completely(self, channel_id: int):
        channel = await self.get_or_404(channel_id)
        
        
        await self.db.execute(delete(UserChannel).where(UserChannel.channel_id == channel_id))
        streams_query = await self.db.execute(select(Stream.id).where(Stream.channel_id == channel_id))
        stream_ids = streams_query.scalars().all()
        if stream_ids:
            await self.db.execute(delete(Danmaku).where(Danmaku.stream_id.in_(stream_ids)))
            await self.db.execute(delete(Stream).where(Stream.id.in_(stream_ids)))
            
        await self.db.execute(delete(Video).where(Video.channel_id == channel_id))
        await self.db.delete(channel)
        await self.db.commit()