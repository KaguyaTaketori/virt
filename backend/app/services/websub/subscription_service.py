from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.database_async import AsyncSessionFactory
from app.models.models import Channel, WebSubSubscription
from .hub_client import hub_client

_LEASE_DAYS = 9

class WebSubSubscriptionService:
    async def subscribe_channel(
        self, channel_db_id: int, callback_url: str, secret: str = ""
    ) -> bool:
        async with AsyncSessionFactory() as session:
            channel = await session.get(Channel, channel_db_id)
            if not channel or channel.platform != "youtube":
                return False

            ok = await hub_client.subscribe(
                channel.channel_id, callback_url, secret=secret
            )
            if ok:
                await self._record_subscription(session, channel)
            return ok

    async def subscribe_all_active(self, callback_url: str) -> None:
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(Channel).where(
                    Channel.platform == "youtube",
                    Channel.is_active.is_(True),
                )
            )
            channels = result.scalars().all()

        import asyncio
        for ch in channels:
            await hub_client.subscribe(ch.channel_id, callback_url)
            await asyncio.sleep(0.3)

    async def _record_subscription(self, session, channel: Channel) -> None:
        sub = await session.scalar(
            select(WebSubSubscription).where(
                WebSubSubscription.channel_id == channel.id
            )
        )
        now = datetime.now(timezone.utc)
        if not sub:
            sub = WebSubSubscription(
                channel_id=channel.id,
                topic_url=f"https://www.youtube.com/xml/feeds/videos.xml?channel_id={channel.channel_id}",
                hub_url="https://pubsubhubbub.appspot.com/",
            )
            session.add(sub)
        sub.subscribed_at = now
        sub.expires_at    = now + timedelta(days=_LEASE_DAYS)
        await session.commit()

websub_service = WebSubSubscriptionService()