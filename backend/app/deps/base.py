from __future__ import annotations
from typing import AsyncGenerator, Generator
from fastapi import Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database_async import AsyncSessionFactory


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_async_db_dep() -> Generator[AsyncSession, None, None]:
    """同步版本的 get_async_db，用于保持向后兼容"""
    raise NotImplementedError("get_db 已迁移到 get_async_db，请使用 async def endpoint")
