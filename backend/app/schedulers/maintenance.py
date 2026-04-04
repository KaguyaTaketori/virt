from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.config import settings
from app.database_async import AsyncSessionFactory
from app.loguru_config import logger
from app.models.models import Channel, Platform
from app.services.youtube_channel import get_channel_details
from app.services.youtube_sync import sync_channel_videos
from app.services.youtube_websub import subscribe_all_active_channels


async def refresh_channel_details():
    """每天执行，刷新所有频道的 banner/描述/链接"""
    if not settings.youtube_api_key:
        return

    async with AsyncSessionFactory() as db:
        result = await db.execute(
            select(Channel).where(
                Channel.platform == Platform.YOUTUBE,
                Channel.is_active == True,
            )
        )
        channels = result.scalars().all()

        if not channels:
            return

        logger.info("开始刷新 {} 个 YouTube 频道", len(channels))

        async with httpx.AsyncClient(timeout=30.0) as client:
            for ch in channels:
                try:
                    details = await get_channel_details(ch.channel_id)
                    if details:
                        changed = False
                        if (
                            details.get("banner_url")
                            and ch.banner_url != details["banner_url"]
                        ):
                            ch.banner_url = details["banner_url"]
                            changed = True
                        if (
                            details.get("description")
                            and ch.description != details["description"]
                        ):
                            ch.description = details["description"]
                            changed = True
                        if (
                            details.get("twitter_url")
                            and ch.twitter_url != details["twitter_url"]
                        ):
                            ch.twitter_url = details["twitter_url"]
                            changed = True
                        if (
                            details.get("youtube_url")
                            and ch.youtube_url != details["youtube_url"]
                        ):
                            ch.youtube_url = details["youtube_url"]
                            changed = True
                        if changed:
                            ch.updated_at = datetime.now(timezone.utc)
                except Exception as e:
                    logger.warning("{}: {}", ch.name, e)

        await db.commit()
        logger.info("完成")

async def daily_backfill_sync():
    """
    每日兜底对账：用 PlaylistItems(UUxxx) 增量同步每个频道的最新50条。
    配额消耗极低：每频道约 2 配额，100频道 ≈ 200 配额/天。
    补漏 WebSub 可能遗漏的视频。
    """
    api_key = settings.youtube_api_key
    if not api_key:
        return

    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Channel).where(
                Channel.platform == Platform.YOUTUBE,
                Channel.is_active == True,
            )
        )
        channels = result.scalars().all()

    for ch in channels:
        async with AsyncSessionFactory() as session:
            ch_obj = await session.get(Channel, ch.id)
            if ch_obj:
                await sync_channel_videos(session, ch_obj, api_key, full_refresh=False)

async def renew_websub():
    """每 8 天续订所有频道的 WebSub 订阅，避免 10 天后过期失效。"""
    callback_url = settings.websub_callback_url
    await subscribe_all_active_channels(callback_url)

