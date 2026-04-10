from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.models import Video, Platform
from app.loguru_config import logger


class VideoRepository(CRUDBase[Video]):
    """Video 实体的 Repository。"""

    def __init__(self, session: AsyncSession):
        super().__init__(Video, session)

    async def get_by_video_id(self, channel_id: int, video_id: str) -> Optional[Video]:
        """通过 channel_id + video_id 组合查询。"""
        query = select(Video).where(
            and_(Video.channel_id == channel_id, Video.video_id == video_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_channel(
        self,
        channel_id: int,
        skip: int = 0,
        limit: int = 24,
        status: Optional[str] = None,
    ) -> list[Video]:
        """获取某个频道的视频列表。"""
        query = select(Video).where(Video.channel_id == channel_id)
        if status is not None:
            query = query.where(Video.status == status)
        query = query.order_by(desc(Video.published_at)).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_paginated_by_channel(
        self,
        channel_id: int,
        page: int = 1,
        page_size: int = 24,
        status: Optional[str] = None,
    ) -> tuple[list[Video], int]:
        """分页获取频道视频。"""
        skip = (page - 1) * page_size

        count_query = (
            select(func.count())
            .select_from(Video)
            .where(Video.channel_id == channel_id)
        )
        if status is not None:
            count_query = count_query.where(Video.status == status)
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        data_query = select(Video).where(Video.channel_id == channel_id)
        if status is not None:
            data_query = data_query.where(Video.status == status)
        data_query = (
            data_query.order_by(desc(Video.published_at)).offset(skip).limit(page_size)
        )

        result = await self.session.execute(data_query)
        return list(result.scalars().all()), total

    async def get_live_and_upcoming(
        self,
        channel_id: int,
        limit: int = 10,
    ) -> list[Video]:
        """获取直播中和新预约的视频。"""
        query = (
            select(Video)
            .where(
                and_(
                    Video.channel_id == channel_id,
                    Video.status.in_(["live", "upcoming"]),
                )
            )
            .order_by(desc(Video.published_at))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_recent_videos(
        self,
        platform: Optional[Platform] = None,
        limit: int = 50,
    ) -> list[Video]:
        """获取最近发布的视频。"""
        query = select(Video)
        if platform is not None:
            query = query.where(Video.platform == platform)
        query = query.order_by(desc(Video.published_at)).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def upsert_video(
        self,
        channel_id: int,
        video_id: str,
        data: dict[str, Any],
    ) -> tuple[Video, bool]:
        """插入或更新视频。"""
        return await self.upsert(
            unique_fields={"channel_id": channel_id, "video_id": video_id},
            obj_in=data,
        )

    async def batch_upsert(
        self,
        channel_id: int,
        videos: list[dict[str, Any]],
    ) -> list[Video]:
        """批量插入或更新视频。"""
        results = []
        for v in videos:
            video, _ = await self.upsert_video(
                channel_id=channel_id,
                video_id=v.get("video_id", ""),
                obj_in=v,
            )
            results.append(video)
        return results

    async def count_by_channel(
        self, channel_id: int, status: Optional[str] = None
    ) -> int:
        """统计频道视频数量。"""
        query = (
            select(func.count())
            .select_from(Video)
            .where(Video.channel_id == channel_id)
        )
        if status is not None:
            query = query.where(Video.status == status)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def delete_batch(
        self,
        channel_id: int,
        video_ids: list[str],
    ) -> int:
        """批量删除视频。"""
        if not video_ids:
            return 0
        query = Video.__table__.delete().where(
            and_(Video.channel_id == channel_id, Video.video_id.in_(video_ids))
        )
        result = await self.session.execute(query)
        return result.rowcount
