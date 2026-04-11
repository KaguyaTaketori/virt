from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.channels import ChannelRepository, UserChannelRepository
from app.integrations.youtube import youtube_service
from app.integrations.bilibili import bilibili_service
from app.models.models import Channel, Platform, UserChannel, Video, Stream, Danmaku
from app.schemas.schemas import ChannelCreate
from app.loguru_config import logger


class ChannelService:
    """业务层：频道管理服务。协调 Repository 和 Integration。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.channel_repo = ChannelRepository(session)
        self.user_channel_repo = UserChannelRepository(session)

    async def get_or_404(self, channel_id: int) -> Channel:
        """获取频道，不存在则抛出 404。"""
        channel = await self.channel_repo.get(channel_id)
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        return channel

    async def get_by_platform_id(
        self,
        platform_channel_id: str,
        platform: Platform,
    ) -> Optional[Channel]:
        """通过平台 ID 查询频道。"""
        return await self.channel_repo.get_by_channel_id(platform_channel_id, platform)

    async def prepare_youtube_data(self, channel_in: ChannelCreate) -> dict:
        """从 YouTube 获取频道元数据。"""
        data = channel_in.model_dump()

        if channel_in.platform == Platform.YOUTUBE:
            resolved_id = channel_in.channel_id
            info = await youtube_service.get_channel_info(channel_in.channel_id)
            if info and info.channel_id:
                resolved_id = info.channel_id
                data["channel_id"] = resolved_id
                data["avatar_url"] = data.get("avatar_url") or info.avatar_url
                data["name"] = data.get("name") or info.name

            details = (
                await youtube_service._get_channel_details_fallback(resolved_id)
                if resolved_id
                else None
            )
            if details:
                fields = ("banner_url", "description", "twitter_url", "youtube_url")
                for field in fields:
                    val = getattr(details, field, None)
                    if not data.get(field) and val:
                        data[field] = val

        return data

    async def prepare_bilibili_data(self, channel_in: ChannelCreate) -> dict:
        """从 Bilibili 获取频道元数据。"""
        data = channel_in.model_dump()

        if channel_in.platform == Platform.BILIBILI:
            info = await bilibili_service.get_channel_info(channel_in.channel_id)
            if info:
                data["avatar_url"] = data.get("avatar_url") or info.avatar_url
                data["name"] = data.get("name") or info.name
                if info.bilibili_sign:
                    data["description"] = info.bilibili_sign

        return data

    async def create_channel(self, channel_in: ChannelCreate) -> Channel:
        """创建频道。"""
        if channel_in.platform == Platform.YOUTUBE:
            processed_data = await self.prepare_youtube_data(channel_in)
        elif channel_in.platform == Platform.BILIBILI:
            processed_data = await self.prepare_bilibili_data(channel_in)
        else:
            processed_data = channel_in.model_dump()

        existing = await self.channel_repo.get_by_channel_id(
            processed_data["channel_id"],
            channel_in.platform,
        )
        if existing:
            raise HTTPException(status_code=400, detail="Channel already exists")

        channel, created = await self.channel_repo.upsert(
            unique_fields={
                "channel_id": processed_data["channel_id"],
                "platform": channel_in.platform,
            },
            obj_in=processed_data,
        )
        if created:
            logger.info(
                "Created new channel: %s (%s)", channel.name, channel.channel_id
            )
        return channel

    async def update_channel(
        self,
        channel_id: int,
        update_data: dict,
    ) -> Channel:
        """更新频道。"""
        channel = await self.get_or_404(channel_id)
        for key, value in update_data.items():
            if value is not None and hasattr(channel, key):
                setattr(channel, key, value)
        await self.session.flush()
        return channel

    async def delete_channel_completely(self, channel_id: int):
        """完全删除频道及其所有关联数据。"""
        channel = await self.get_or_404(channel_id)

        stream_ids_query = await self.session.execute(
            select(Stream.id).where(Stream.channel_id == channel_id)
        )
        stream_ids = stream_ids_query.scalars().all()

        if stream_ids:
            await self.session.execute(
                delete(Danmaku).where(Danmaku.stream_id.in_(stream_ids))
            )
            await self.session.execute(delete(Stream).where(Stream.id.in_(stream_ids)))

        await self.session.execute(delete(Video).where(Video.channel_id == channel_id))
        await self.session.delete(channel)
        await self.session.flush()
        logger.info("Deleted channel completely: id=%d", channel_id)
        return True

    async def set_user_status(
        self,
        user_id: int,
        channel_id: int,
        status: str,
    ) -> UserChannel:
        """设置用户对频道的关注状态。"""
        await self.get_or_404(channel_id)
        return await self.user_channel_repo.set_status(user_id, channel_id, status)

    async def remove_user_status(
        self,
        user_id: int,
        channel_id: int,
    ) -> bool:
        """移除用户对频道的关注状态。"""
        return await self.user_channel_repo.remove_status(user_id, channel_id)


__all__ = ["ChannelService"]
