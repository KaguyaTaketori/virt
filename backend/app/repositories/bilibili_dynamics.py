from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy import select, desc

from app.database.base import BaseRepository
from app.models.models import BilibiliDynamic


class BilibiliDynamicRepository(BaseRepository[BilibiliDynamic]):
    """B站动态实体的 Repository。"""

    model = BilibiliDynamic

    async def get_by_channel(
        self,
        channel_id: int,
        limit: int = 12,
    ) -> list[BilibiliDynamic]:
        """获取某个频道的动态列表。"""
        query = (
            select(BilibiliDynamic)
            .where(BilibiliDynamic.channel_id == channel_id)
            .order_by(desc(BilibiliDynamic.timestamp))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_paginated_by_channel(
        self,
        channel_id: int,
        page: int = 1,
        page_size: int = 12,
    ) -> tuple[list[BilibiliDynamic], int]:
        """分页获取频道动态。"""
        skip = (page - 1) * page_size

        count_query = select(BilibiliDynamic).where(
            BilibiliDynamic.channel_id == channel_id
        )
        count_result = await self.session.execute(
            select(count_query.alias()).columns.id.count()
        )
        total = count_result.scalar() or 0

        query = (
            select(BilibiliDynamic)
            .where(BilibiliDynamic.channel_id == channel_id)
            .order_by(desc(BilibiliDynamic.timestamp))
            .offset(skip)
            .limit(page_size)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def upsert_dynamic(
        self,
        channel_id: int,
        dynamic_id: str,
        data: dict[str, Any],
    ) -> tuple[BilibiliDynamic, bool]:
        """插入或更新动态。"""
        return await self.upsert(
            unique_fields={"dynamic_id": dynamic_id},
            obj_in=data,
        )
