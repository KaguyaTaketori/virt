from __future__ import annotations
import logging

from sqlalchemy import event
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()


def _to_async_url(db_url: str) -> str:
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if db_url.startswith("postgresql://") or db_url.startswith("postgres://"):
        return db_url.replace("postgresql://", "postgresql+asyncpg://", 1).replace(
            "postgres://", "postgresql+asyncpg://", 1
        )
    return db_url


_ASYNC_URL: str = _to_async_url(settings.db_url)
_IS_SQLITE = _ASYNC_URL.startswith("sqlite+aiosqlite")

_connect_args: dict = {}
_engine_kwargs: dict = {
    "echo": False,
    "pool_pre_ping": True,
}

if _IS_SQLITE:
    _connect_args = {"check_same_thread": False, "timeout": 60}
else:
    _engine_kwargs.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_recycle": 1800,
        }
    )


engine = create_async_engine(_ASYNC_URL, connect_args=_connect_args, **_engine_kwargs)


if _IS_SQLITE:

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _record) -> None:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA cache_size=10000")
        cur.execute("PRAGMA temp_store=MEMORY")
        cur.execute("PRAGMA mmap_size=134217728")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()


AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def create_all_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified/created.")


async def dispose_engine() -> None:
    await engine.dispose()
