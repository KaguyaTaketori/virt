import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.loguru_config import logger
from app.models.models import BilibiliDynamic, Platform, Video

class BilibiliRepository:
    async def upsert_dynamics(
        self,
        db: AsyncSession,
        channel_id: int,
        parsed_dynamics: list[dict],
        raw_dynamics: list[dict],
    ) -> None:
        for parsed, raw in zip(parsed_dynamics, raw_dynamics):
            await self._upsert_single_dynamic(db, channel_id, parsed, raw)
        await db.commit()

    async def upsert_videos(
        self, db: AsyncSession, channel_id: int, videos: list[dict]
    ) -> None:
        for v in videos:
            await self._upsert_single_video(db, channel_id, v)
        await db.commit() 

    async def _upsert_single_dynamic(self, db, channel_id, parsed, raw):
        try:
            dynamic_id = parsed.get("dynamic_id", "")
            if not dynamic_id:
                return

            result = await db.execute(
                select(BilibiliDynamic).where(BilibiliDynamic.dynamic_id == dynamic_id)
            )
            existing = result.scalar_one_or_none()

            published = None
            ts = parsed.get("timestamp")
            if ts:
                try:
                    published = datetime.fromtimestamp(ts, tz=timezone.utc)
                except Exception:
                    pass

            content_nodes_json = json.dumps(
                parsed.get("content_nodes", []), ensure_ascii=False
            )
            images_json = json.dumps(parsed.get("images", []), ensure_ascii=False)
            stat_json = json.dumps(parsed.get("stat", {}), ensure_ascii=False)

            if existing:
                existing.uname = parsed.get("uname")
                existing.face = parsed.get("face")
                existing.type = parsed.get("type")
                existing.content_nodes = content_nodes_json
                existing.images = images_json
                existing.repost_content = parsed.get("repost_content")
                existing.timestamp = ts
                existing.published_at = published
                existing.url = parsed.get("url")
                existing.stat = stat_json
                existing.topic = parsed.get("topic")
                existing.is_top = parsed.get("is_top", False)
                existing.raw_data = json.dumps(raw, ensure_ascii=False)
                existing.fetched_at = datetime.now(timezone.utc)
            else:
                dynamic = BilibiliDynamic(
                    channel_id=channel_id,
                    dynamic_id=dynamic_id,
                    uid=parsed.get("uid"),
                    uname=parsed.get("uname"),
                    face=parsed.get("face"),
                    type=parsed.get("type"),
                    content_nodes=content_nodes_json,
                    images=images_json,
                    repost_content=parsed.get("repost_content"),
                    timestamp=ts,
                    published_at=published,
                    url=parsed.get("url"),
                    stat=stat_json,
                    topic=parsed.get("topic"),
                    is_top=parsed.get("is_top", False),
                    raw_data=json.dumps(raw, ensure_ascii=False),
                    fetched_at=datetime.now(timezone.utc),
                )
                db.add(dynamic)
        except Exception as e:
            logger.warning("Failed to save dynamic new: {}", e)

    async def _upsert_single_video(self, db, channel_id, v):
        try:
            bvid = v.get("bvid", "")
            if not bvid:
                return

            result = await db.execute(
                select(Video).where(
                    Video.channel_id == channel_id, Video.video_id == bvid
                )
            )
            existing = result.scalar_one_or_none()

            published = None
            if v.get("created"):
                try:
                    published = datetime.fromtimestamp(v.get("created"))
                except Exception:
                    pass

            if existing:
                existing.title = v.get("title")
                existing.thumbnail_url = v.get("pic", "")
                existing.view_count = v.get("play", 0)
                existing.duration = v.get("length", "")
                existing.published_at = published
            else:
                video = Video(
                    channel_id=channel_id,
                    platform=Platform.BILIBILI,
                    video_id=bvid,
                    title=v.get("title", ""),
                    thumbnail_url=v.get("pic", ""),
                    duration=v.get("length", ""),
                    view_count=v.get("play", 0),
                    published_at=published,
                    status="archive",
                )
                db.add(video)

            await db.commit()
        except Exception as e:
            logger.warning("Failed to save video: {}", e)