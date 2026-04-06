from __future__ import annotations

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User
from app.loguru_config import logger


class BilibiliUserService:
    async def get_credential(
        self,
        user_id: int,
        db: AsyncSession,
    ) -> Optional[dict]:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None

        if not user.bilibili_sessdata:
            return None

        return {
            "sessdata": user.bilibili_sessdata,
            "bili_jct": user.bilibili_bili_jct,
            "buvid3": user.bilibili_buvid3,
            "dedeuserid": user.bilibili_dedeuserid,
        }

    async def save_credential(
        self,
        user_id: int,
        sessdata: str,
        bili_jct: str,
        buvid3: str,
        dedeuserid: Optional[str] = None,
        db: AsyncSession = None,
    ) -> bool:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            logger.warning("User not found, user_id={}", user_id)
            return False

        user.bilibili_sessdata = sessdata
        user.bilibili_bili_jct = bili_jct
        user.bilibili_buvid3 = buvid3
        user.bilibili_dedeuserid = dedeuserid

        await db.commit()
        logger.info("Bilibili credentials saved, user_id={}", user_id)
        return True

    async def has_credential(
        self,
        user_id: int,
        db: AsyncSession,
    ) -> bool:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False
        return bool(user.bilibili_sessdata)

    async def delete_credential(
        self,
        user_id: int,
        db: AsyncSession,
    ) -> bool:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False

        user.bilibili_sessdata = None
        user.bilibili_bili_jct = None
        user.bilibili_buvid3 = None
        user.bilibili_dedeuserid = None

        await db.commit()
        logger.info("Bilibili credentials deleted, user_id={}", user_id)
        return True


bilibili_user_service = BilibiliUserService()
