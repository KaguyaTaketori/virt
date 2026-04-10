import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.loguru_config import logger
from app.models.models import BilibiliDynamic, Platform, Video
from app.db_utils import upsert_batch, _insert_fn


class BilibiliRepository:
    async def upsert_dynamics(
        self,
        db: AsyncSession,
        channel_id: int,
        parsed_dynamics: list[dict],
        raw_dynamics: list[dict],
    ) -> None:
        if not parsed_dynamics: return

        batch_values = []
        for parsed, raw in zip(parsed_dynamics, raw_dynamics):
            dynamic_id = parsed.get("dynamic_id")
            if not dynamic_id: continue
            
            ts = parsed.get("timestamp")
            batch_values.append({
                "channel_id": channel_id,
                "dynamic_id": str(dynamic_id),
                "uid": parsed.get("uid"),
                "uname": parsed.get("uname"),
                "face": parsed.get("face"),
                "type": parsed.get("type"),
                "content_nodes": json.dumps(parsed.get("content_nodes", []), ensure_ascii=False),
                "images": json.dumps(parsed.get("images", []), ensure_ascii=False),
                "repost_content": parsed.get("repost_content"),
                "timestamp": ts,
                "published_at": datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None,
                "url": parsed.get("url"),
                "stat": json.dumps(parsed.get("stat", {}), ensure_ascii=False),
                "topic": parsed.get("topic"),
                "is_top": parsed.get("is_top", False),
                "raw_data": json.dumps(raw, ensure_ascii=False),
                "fetched_at": datetime.now(timezone.utc),
            })

        stmt = _insert_fn(BilibiliDynamic) 
        update_cols = {
            "uname": stmt.excluded.uname,
            "face": stmt.excluded.face,
            "stat": stmt.excluded.stat,
            "is_top": stmt.excluded.is_top,
            "content_nodes": stmt.excluded.content_nodes,
            "fetched_at": stmt.excluded.fetched_at,
        }

        await upsert_batch(
            db, BilibiliDynamic, ["dynamic_id"], batch_values, update_cols
        )
        await db.commit()

    async def upsert_videos(
        self, db: AsyncSession, channel_id: int, videos: list[dict]
    ) -> None:
        if not videos: return

        batch_values = []
        for v in videos:
            bvid = v.get("bvid")
            if not bvid: continue
            
            batch_values.append({
                "channel_id": channel_id,
                "platform": Platform.BILIBILI,
                "video_id": bvid,
                "title": v.get("title", ""),
                "thumbnail_url": v.get("pic", ""),
                "duration": v.get("length", ""),
                "view_count": v.get("play", 0),
                "published_at": datetime.fromtimestamp(v["created"]) if v.get("created") else None,
                "status": "archive",
            })

        stmt = _insert_fn(Video)
        update_cols = {
            "title": stmt.excluded.title,
            "thumbnail_url": stmt.excluded.thumbnail_url,
            "view_count": stmt.excluded.view_count,
        }

        await upsert_batch(
            db, Video, ["channel_id", "video_id"], batch_values, update_cols
        )
        await db.commit()