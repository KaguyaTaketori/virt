from __future__ import annotations

from typing import Optional

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.integrations.bili_client import BiliClient, get_bili_client
from app.integrations.youtube import YouTubeSyncService, get_youtube_client
from app.repositories import ChannelRepository, StreamRepository
from app.services.channel_service import ChannelService
from app.services.redis_client import RedisClient


async def get_redis() -> Optional[Redis]:
    """获取 Redis 实例"""
    try:
        return await RedisClient.get_client()
    except Exception:
        return None


async def _get_channel_repo(
    session: AsyncSession = Depends(get_db_session),
) -> ChannelRepository:
    return ChannelRepository(session)


async def _get_stream_repo(
    session: AsyncSession = Depends(get_db_session),
) -> StreamRepository:
    return StreamRepository(session)


async def get_channel_service(
    session: AsyncSession = Depends(get_db_session),
    channel_repo: ChannelRepository = Depends(_get_channel_repo),
    stream_repo: StreamRepository = Depends(_get_stream_repo),
    bili_client: BiliClient = Depends(get_bili_client),
    youtube_client: YouTubeSyncService = Depends(get_youtube_client),
    redis: Optional[Redis] = Depends(get_redis),
) -> ChannelService:
    """ChannelService 依赖注入"""
    return ChannelService(
        session=session,
        channel_repo=channel_repo,
        stream_repo=stream_repo,
        bili_client=bili_client,
        youtube_client=youtube_client,
        redis=redis,
    )


__all__ = ["get_channel_service", "ChannelService"]
