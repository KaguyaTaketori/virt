from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import BaseRepository
from app.models.models import Stream, Platform, StreamStatus
from app.loguru_config import logger


class StreamRepository(BaseRepository[Stream]):
    """Stream 实体的 Repository。"""

    model = Stream

    async def get_by_video_id(self, channel_id: int, video_id: str) -> Optional[Stream]:
        """通过 channel_id + video_id 查询。"""
        query = select(Stream).where(
            and_(Stream.channel_id == channel_id, Stream.video_id == video_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_live_streams(
        self,
        platform: Optional[Platform] = None,
    ) -> list[Stream]:
        """获取当前直播中的流。"""
        query = select(Stream).where(Stream.status == StreamStatus.LIVE)
        if platform is not None:
            query = query.where(Stream.platform == platform)
        query = query.order_by(Stream.viewer_count.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_upcoming_streams(
        self,
        platform: Optional[Platform] = None,
        limit: int = 20,
    ) -> list[Stream]:
        """获取即将开始的预约直播。"""
        query = select(Stream).where(Stream.status == StreamStatus.UPCOMING)
        if platform is not None:
            query = query.where(Stream.platform == platform)
        if limit:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_channel(
        self,
        channel_id: int,
        status: Optional[StreamStatus] = None,
        limit: int = 10,
    ) -> list[Stream]:
        """获取某个频道的流。"""
        query = select(Stream).where(Stream.channel_id == channel_id)
        if status is not None:
            query = query.where(Stream.status == status)
        query = query.order_by(desc(Stream.started_at)).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def upsert_stream(
        self,
        channel_id: int,
        video_id: str,
        data: dict[str, Any],
    ) -> tuple[Stream, bool]:
        """插入或更新流。"""
        return await self.upsert(
            unique_fields={"channel_id": channel_id, "video_id": video_id},
            obj_in=data,
        )

    async def update_viewer_count(self, stream_id: int, viewer_count: int) -> bool:
        """更新观看人数。"""
        stream = await self.get(stream_id)
        if stream:
            stream.viewer_count = viewer_count
            if viewer_count > (stream.peak_viewers or 0):
                stream.peak_viewers = viewer_count
            await self.session.flush()
            return True
        return False

    async def update_status(
        self,
        stream_id: int,
        status: StreamStatus,
        ended_at: Optional[datetime] = None,
    ) -> bool:
        """更新流的状态。"""
        stream = await self.get(stream_id)
        if stream:
            stream.status = status
            if status == StreamStatus.LIVE and not stream.started_at:
                stream.started_at = datetime.now(timezone.utc)
            if status == StreamStatus.ARCHIVE and ended_at:
                stream.ended_at = ended_at
            await self.session.flush()
            return True
        return False

    async def terminate_channel_streams(self, channel_id: int) -> int:
        """终止频道的所有活跃流。"""
        query = (
            Stream.__table__.update()
            .where(
                and_(
                    Stream.channel_id == channel_id,
                    Stream.status.in_([StreamStatus.LIVE, StreamStatus.UPCOMING]),
                )
            )
            .values(status=StreamStatus.ARCHIVE, ended_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(query)
        return result.rowcount

    def _normalize_status(self, data: dict[str, Any]) -> dict[str, Any]:
        """规范化 status 字段为枚举值"""
        result = data.copy()
        status_str = result.get("status")
        if status_str and isinstance(status_str, str):
            try:
                result["status"] = StreamStatus(status_str)
            except ValueError:
                result["status"] = StreamStatus.OFFLINE
        return result

    async def upsert_atomic(
        self,
        channel_id: int,
        video_id: str,
        **data,
    ) -> tuple[Stream, bool]:
        """原子化 upsert：查找或创建 Stream"""
        data = self._normalize_status(data)

        existing = await self.get_by_video_id(channel_id, video_id)
        if existing:
            for k, v in data.items():
                if v is not None and hasattr(existing, k):
                    setattr(existing, k, v)
            await self.session.flush()
            return existing, False

        stream = Stream(channel_id=channel_id, video_id=video_id, **data)
        self.session.add(stream)
        await self.session.flush()
        return stream, True
