import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select

from app.models.models import Channel, WebSubSubscription
from app.services.api_key_manager import is_api_available
from app.integrations.youtube import get_youtube_sync_service
from app.database import session_scope
from app.repositories import ChannelRepository
from app.integrations.websub.hub_client import hub_client


class WebSubSubscriptionService:
    def __init__(self, lease_days: int = 9):
        self.lease_days = lease_days
        self._hub = hub_client

    async def subscribe_channel(
        self, channel_db_id: int, callback_url: str, secret: str = ""
    ) -> bool:
        async with session_scope() as session:
            channel_repo = ChannelRepository(session)
            channel = await channel_repo.get(channel_db_id)
            if not channel or channel.platform.value != "youtube":
                return False

            ok = await self._hub.subscribe(
                channel.channel_id,
                callback_url,
                secret=secret,
                lease_seconds=self.lease_days * 86400,
            )
            if ok:
                await self._record_subscription(session, channel, secret)
            return ok

    async def subscribe_all_active(self, callback_url: str, secret: str = "") -> None:
        async with session_scope() as session:
            channel_repo = ChannelRepository(session)
            channels = await channel_repo.get_active_channels("youtube")

        for ch in channels:
            ok = await self._hub.subscribe(ch.channel_id, callback_url, secret=secret)
            if ok:
                async with session_scope() as sub_session:
                    await self._record_subscription(sub_session, ch, secret)
            await asyncio.sleep(0.3)

    async def confirm_verification(self, yt_channel_id: str, mode: str) -> None:
        if mode != "subscribe":
            return
        async with session_scope() as session:
            channel = await session.scalar(
                select(Channel).where(
                    Channel.channel_id == yt_channel_id, Channel.platform == "youtube"
                )
            )
            if not channel:
                return

            sub = await session.scalar(
                select(WebSubSubscription).where(
                    WebSubSubscription.channel_id == channel.id
                )
            )
            if sub:
                sub.verified = True

    async def process_video_notification(
        self, yt_channel_id: str, video_id: str
    ) -> None:
        if not await is_api_available():
            return

        async with session_scope() as session:
            channel = await session.scalar(
                select(Channel).where(
                    Channel.channel_id == yt_channel_id, Channel.platform == "youtube"
                )
            )
            if not channel:
                return

            yt_service = get_youtube_sync_service()
            video = await yt_service.fetch_and_upsert_single_video(
                session, channel, video_id
            )

            if video:
                sub = await session.scalar(
                    select(WebSubSubscription).where(
                        WebSubSubscription.channel_id == channel.id
                    )
                )
                if sub:
                    sub.last_push_at = datetime.now(timezone.utc)
                    sub.push_count = (sub.push_count or 0) + 1

    async def _record_subscription(
        self, session, channel: Channel, secret: str
    ) -> Optional[WebSubSubscription]:
        sub = await session.scalar(
            select(WebSubSubscription).where(
                WebSubSubscription.channel_id == channel.id
            )
        )
        now = datetime.now(timezone.utc)
        if not sub:
            sub = WebSubSubscription(
                channel_id=channel.id,
                topic_url=f".xml?channel_id={channel.channel_id}",
                hub_url="https://pubsubhubbub.appspot.com/",
                secret=secret or None,
            )
            session.add(sub)
        sub.subscribed_at = now
        sub.expires_at = now + timedelta(days=self.lease_days)
        return sub


websub_service = WebSubSubscriptionService()
