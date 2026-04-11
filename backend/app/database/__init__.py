from __future__ import annotations

from app.database.engine import (
    Base,
    engine,
    AsyncSessionFactory,
    create_all_tables,
    dispose_engine,
)
from app.database.session import (
    session_scope,
    get_db_session,
)
from app.database.utils import (
    upsert,
    upsert_batch,
    upsert_stream,
    _insert_fn,
)
from app.database.base import (
    BaseRepository,
    PagedRepository,
)

__all__ = [
    # Engine
    "Base",
    "engine",
    "AsyncSessionFactory",
    "create_all_tables",
    "dispose_engine",
    # Session
    "session_scope",
    "get_db_session",
    # Utils
    "upsert",
    "upsert_batch",
    "upsert_stream",
    # Base classes
    "BaseRepository",
    "PagedRepository",
]
