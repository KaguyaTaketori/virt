from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.config import settings


def get_insert_fn():
    if settings.is_postgresql:
        return pg_insert
    return sqlite_insert


_insert_fn = get_insert_fn()


async def upsert(
    session: AsyncSession,
    model,
    values: dict,
    index_elements: list[str],
    update_cols: dict,
) -> None:
    stmt = _insert_fn(model).values(**values)
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=index_elements,
        set_=update_cols,
    )
    await session.execute(upsert_stmt)