# backend/app/database.py
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

from app.config import settings  # ✅ 统一来源

# 同步引擎只做迁移/种子数据使用，保持同步 URL 格式
_sync_url = settings.db_url  # "sqlite:///./streams.db" 或 "postgresql://..."

engine = create_engine(
    _sync_url,
    connect_args={"check_same_thread": False, "timeout": 30}
    if _sync_url.startswith("sqlite") else {},
    poolclass=StaticPool if _sync_url.startswith("sqlite") else None,
    echo=False,
)

# SQLite 专属 PRAGMA（与 database_async.py 保持一致）
if _sync_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        for pragma in [
            "PRAGMA journal_mode=WAL",
            "PRAGMA synchronous=NORMAL",
            "PRAGMA cache_size=10000",
            "PRAGMA temp_store=MEMORY",
            "PRAGMA mmap_size=134217728",
            "PRAGMA encoding='UTF-8'",
        ]:
            cur.execute(pragma)
        cur.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()