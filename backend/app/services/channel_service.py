from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.bili_client import BiliClient
from app.integrations.youtube import YouTubeSyncService
from app.loguru_config import logger
from app.models.models import Channel, Platform, UserChannel, Video, Stream, Danmaku
from app.repositories import ChannelRepository, StreamRepository, UserChannelRepository
from app.schemas.schemas import ChannelCreate
from app.integrations.platform_registry import get_platform


class ChannelService:
    """业务层：频道管理服务。协调 Repository 和 Integration。"""

    def __init__(
        self,
        session: AsyncSession,
        channel_repo: ChannelRepository,
        stream_repo: StreamRepository,
        bili_client: BiliClient,
        youtube_service: YouTubeSyncService,
        redis: Optional[Redis] = None,
        user_channel_repo: Optional[UserChannelRepository] = None,
    ):
        self.session = session
        self.channel_repo = channel_repo
        self.stream_repo = stream_repo
        self.bili_client = bili_client
        self.yt_service = youtube_service
        self.redis = redis
        self.user_channel_repo = user_channel_repo or UserChannelRepository(session)

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
            info = await self.yt_service.get_channel_info(channel_in.channel_id)
            if info and hasattr(info, "channel_id") and info.channel_id:
                resolved_id = info.channel_id
                data["channel_id"] = resolved_id
                data["avatar_url"] = data.get("avatar_url") or getattr(
                    info, "avatar_url", None
                )
                data["name"] = data.get("name") or getattr(info, "name", None)

            details = (
                await self.yt_service._get_channel_info_fallback(resolved_id)
                if resolved_id
                else None
            )
            if details:
                fields = ("banner_url", "description", "twitter_url", "youtube_url")
                for field in fields:
                    val = (
                        getattr(details, field, None)
                        if hasattr(details, field)
                        else None
                    )
                    if not data.get(field) and val:
                        data[field] = val

        return data

    async def prepare_bilibili_data(self, channel_in: ChannelCreate) -> dict:
        """从 Bilibili 获取频道元数据。"""
        data = channel_in.model_dump()

        if channel_in.platform == Platform.BILIBILI:
            info = await self.bili_client.get_channel_info(channel_in.channel_id)
            if info:
                data["avatar_url"] = data.get("avatar_url") or info.face
                data["name"] = data.get("name") or info.name
                if info.sign:
                    data["description"] = info.sign

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
                "Created new channel: {} ({})", channel.name, channel.channel_id
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
        logger.info("Deleted channel completely: id={}", channel_id)
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

    async def sync_channel_status(self, channel_id: int) -> tuple[Stream, bool]:
        """同步单个频道的直播状态"""
        channel = await self.channel_repo.get(channel_id)
        if not channel:
            raise ValueError(f"Channel {channel_id} not found")

        prev_stream = None
        prev_status = "offline"
        existing_streams = await self.stream_repo.get_by_channel(channel_id, limit=1)
        if existing_streams:
            prev_stream = existing_streams[0]
            prev_status = prev_stream.status.value if prev_stream.status else "offline"

        platform_client = get_platform(channel.platform)
        if platform_client is None:
            logger.warning("No client registered for platform: {}", channel.platform)
            return None, False

        live_status = await platform_client.get_live_status(channel.channel_id)

        if live_status is None:
            return None, False

        update_data = {
            "platform": channel.platform,
            "video_id": getattr(live_status, "video_id", None) or "offline",
            "title": getattr(live_status, "title", None),
            "thumbnail_url": getattr(live_status, "thumbnail_url", None),
            "status": getattr(live_status, "status", "offline"),
            "viewer_count": getattr(live_status, "viewer_count", 0) or 0,
            "started_at": getattr(live_status, "started_at", None),
            "scheduled_at": getattr(live_status, "scheduled_at", None),
        }

        video_id = update_data["video_id"] or "offline"
        stream, created = await self.stream_repo.upsert_atomic(
            channel.id, video_id, **update_data
        )

        if self.redis and prev_status == "offline" and live_status.status == "live":
            await self._publish_live_started(channel, stream)

        return stream, created

    async def sync_channels_batch(
        self, channel_ids: list[int]
    ) -> dict[int, tuple[Stream, bool]]:
        """批量同步多个频道状态"""
        results = {}
        for cid in channel_ids:
            try:
                result = await self.sync_channel_status(cid)
                results[cid] = result
            except Exception as e:
                logger.warning("同步频道 {} 失败: {}", cid, e)
                results[cid] = (None, False)
        return results

    async def _publish_live_started(self, channel: Channel, stream: Stream):
        """发布直播开始消息到 Redis"""
        if not self.redis:
            return

        try:
            channel_key = f"live:{channel.platform.value}:{channel.channel_id}"
            payload = {
                "event": "live_started",
                "channel_id": channel.id,
                "channel_name": channel.name,
                "stream_id": stream.id,
                "video_id": stream.video_id,
                "title": stream.title,
            }
            await self.redis.publish(channel_key, str(payload))
            logger.info("Published live_started: channel={}", channel.channel_id)
        except Exception as e:
            logger.error("Failed to publish live_started: {}", e)


__all__ = ["ChannelService"]
