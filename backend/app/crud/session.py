from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database_async import AsyncSessionFactory
from app.loguru_config import logger


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """
    异步上下文管理器，为后台任务提供 Session。

    用法:
        async with session_scope() as session:
            channel_repo = ChannelRepository(session)
            await channel_repo.get(1)
    """
    session = AsyncSessionFactory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Dependency Injection 用的 Session 提供器。
    与 session_scope 等价，但适配 FastAPI 的 Depends 机制。
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
