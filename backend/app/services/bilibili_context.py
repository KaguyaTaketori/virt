from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from bilibili_api import Credential
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class ChannelRequestContext:
    db: AsyncSession
    channel_id: int
    credential: Optional[Credential]

    @classmethod
    async def build(
        cls,
        db: AsyncSession,
        channel_id: int,
        current_user,
        bilibili_user_service,
    ) -> "ChannelRequestContext":
        credential = None

        if current_user is not None:
            user_cred = await bilibili_user_service.get_credential(
                current_user.id, db
            )
            if user_cred:
                try:
                    credential = Credential(
                        sessdata=user_cred["sessdata"],
                        bili_jct=user_cred["bili_jct"],
                        buvid3=user_cred["buvid3"],
                        dedeuserid=user_cred.get("dedeuserid"),
                    )
                except Exception as e:
                    from app.loguru_config import logger
                    logger.warning("Failed to build user credential: {}", e)

        if credential is None and hasattr(__import__("app.config", fromlist=["settings"]), "settings"):
            from app.config import settings
            if settings.bilibili_sessdata:
                try:
                    credential = Credential(sessdata=settings.bilibili_sessdata)
                except Exception:
                    pass

        return cls(db=db, channel_id=channel_id, credential=credential)