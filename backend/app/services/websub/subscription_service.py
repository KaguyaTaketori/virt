import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.database_async import AsyncSessionFactory
from app.models.models import Channel, WebSubSubscription
from app.loguru_config import logger
from app.services.youtube_sync import fetch_and_upsert_single_video
from app.services.api_key_manager import get_api_key, is_api_available
from .hub_client import hub_client

class WebSubSubscriptionService:
    def __init__(self, lease_days: int = 9):
        self.lease_days = lease_days

    async def subscribe_channel(self, channel_db_id: int, callback_url: str, secret: str = "") -> bool:
        async with AsyncSessionFactory() as session:
            channel = await session.get(Channel, channel_db_id)
            if not channel or channel.platform != "youtube":
                return False

            ok = await hub_client.subscribe(
                channel.channel_id, callback_url, secret=secret, lease_seconds=self.lease_days * 86400
            )
            if ok:
                await self._record_subscription(session, channel, secret)
            return ok

    async def subscribe_all_active(self, callback_url: str, secret: str = "") -> None:
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(Channel).where(Channel.platform == "youtube", Channel.is_active.is_(True))
            )
            channels = result.scalars().all()

        for ch in channels:
            ok = await hub_client.subscribe(ch.channel_id, callback_url, secret=secret)
            if ok:
                async with AsyncSessionFactory() as sub_session:
                    await self._record_subscription(sub_session, ch, secret)
            await asyncio.sleep(0.3)

    async def confirm_verification(self, yt_channel_id: str, mode: str) -> None:
        if mode != "subscribe":
            return
        async with AsyncSessionFactory() as session:
            channel = await session.scalar(
                select(Channel).where(Channel.channel_id == yt_channel_id, Channel.platform == "youtube")
            )
            if channel:
                sub = await session.scalar(
                    select(WebSubSubscription).where(WebSubSubscription.channel_id == channel.id)
                )
                if sub:
                    sub.verified = True
                    await session.commit()

    async def process_video_notification(self, yt_channel_id: str, video_id: str):
        if not await is_api_available():
            return
        api_key = await get_api_key()
        
        async with AsyncSessionFactory() as session:
            channel = await session.scalar(
                select(Channel).where(Channel.channel_id == yt_channel_id, Channel.platform == "youtube")
            )
            if not channel: return

            video = await fetch_and_upsert_single_video(session, channel, video_id, api_key)

            if video:
                sub = await session.scalar(
                    select(WebSubSubscription).where(WebSubSubscription.channel_id == channel.id)
                )
                if sub:
                    sub.last_push_at = datetime.now(timezone.utc)
                    sub.push_count = (sub.push_count or 0) + 1
                    await session.commit()

    async def _record_subscription(self, session, channel: Channel, secret: str) -> None:
        sub = await session.scalar(
            select(WebSubSubscription).where(WebSubSubscription.channel_id == channel.id)
        )
        now = datetime.now(timezone.utc)
        if not sub:
            sub = WebSubSubscription(
                channel_id=channel.id,
                topic_url=f".xml?channel_id={channel.channel_id}",
                hub_url="https://pubsubhubbub.appspot.com/",
                secret=secret or None
            )
            session.add(sub)
        sub.subscribed_at = now
        sub.expires_at = now + timedelta(days=self.lease_days)
        await session.commit()

websub_service = WebSubSubscriptionService()