from __future__ import annotations
from datetime import datetime, timezone

from sqlalchemy import case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.config import settings
from app.models.models import Platform, Stream


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


async def upsert_stream(
    db: AsyncSession,
    channel_id: int,
    parsed: dict,
    platform: Platform,
) -> None:
    now = datetime.now(timezone.utc)
    
    insert_data = {
        "channel_id": channel_id,
        "platform": platform,
        "video_id": parsed["video_id"],
        "title": parsed.get("title"),
        "status": parsed.get("status"),
        "viewer_count": parsed.get("viewer_count", 0),
        "updated_at": now,
    }
    
    stmt = _insert_fn(Stream).values(**insert_data)
    
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=["channel_id", "video_id"],
        set_={
            "title": stmt.excluded.title,
            "status": stmt.excluded.status,
            "viewer_count": stmt.excluded.viewer_count,
            "updated_at": now,
            # 仅在新值更大时更新peak_viewers
            "peak_viewers": case(
                (stmt.excluded.viewer_count > Stream.peak_viewers,
                 stmt.excluded.viewer_count),
                else_=Stream.peak_viewers,
            ),
        },
    )
    
    await db.execute(upsert_stmt)