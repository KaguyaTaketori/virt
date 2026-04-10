from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase, CRUDPaged
from app.models.models import Channel, Organization, Platform, UserChannel, Stream
from app.loguru_config import logger


class ChannelRepository(CRUDBase[Channel]):
    """Channel 实体的 Repository。"""

    def __init__(self, session: AsyncSession):
        super().__init__(Channel, session)

    async def get_by_channel_id(
        self, platform_channel_id: str, platform: Platform
    ) -> Optional[Channel]:
        """通过 platform + channel_id 组合查询。"""
        query = select(Channel).where(
            and_(
                Channel.channel_id == platform_channel_id, Channel.platform == platform
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_org(
        self, org_id: int, is_active: Optional[bool] = None
    ) -> list[Channel]:
        """获取某个组织下的所有频道。"""
        query = select(Channel).where(Channel.org_id == org_id)
        if is_active is not None:
            query = query.where(Channel.is_active == is_active)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_active_channels(
        self, platform: Optional[Platform] = None
    ) -> list[Channel]:
        """获取所有活跃的频道。"""
        query = select(Channel).where(Channel.is_active == True)
        if platform is not None:
            query = query.where(Channel.platform == platform)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search_by_name(self, name: str, limit: int = 20) -> list[Channel]:
        """通过名称模糊搜索。"""
        query = select(Channel).where(Channel.name.ilike(f"%{name}%")).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_paginated(
        self,
        page: int = 1,
        page_size: int = 24,
        platform: Optional[Platform] = None,
        org_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        group: Optional[str] = None,
    ) -> tuple[list[Channel], int]:
        """分页查询频道。"""
        conditions = []
        if platform is not None:
            conditions.append(Channel.platform == platform)
        if org_id is not None:
            conditions.append(Channel.org_id == org_id)
        if is_active is not None:
            conditions.append(Channel.is_active == is_active)
        if group is not None:
            conditions.append(Channel.group == group)

        skip = (page - 1) * page_size

        count_query = select(func.count()).select_from(Channel)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        data_query = select(Channel)
        if conditions:
            data_query = data_query.where(and_(*conditions))
        data_query = data_query.order_by(Channel.name).offset(skip).limit(page_size)

        result = await self.session.execute(data_query)
        return list(result.scalars().all()), total

    async def update_last_fetched(self, channel_id: int) -> None:
        """更新 videos_last_fetched 时间戳。"""
        channel = await self.get(channel_id)
        if channel:
            channel.videos_last_fetched = datetime.utcnow()
            await self.session.flush()

    async def get_with_streams(self, channel_id: int) -> Optional[Channel]:
        """获取频道及其关联的 Stream 列表。"""
        query = (
            select(Channel)
            .options(selectinload(Channel.streams))
            .where(Channel.id == channel_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_channels_with_status(
        self,
        user_id: int,
        platform: Optional[Platform] = None,
    ) -> list[tuple[Channel, Optional[str]]]:
        """
        获取频道及其用户关注状态。
        返回 (Channel, user_channel_status) 列表。
        """
        query = select(Channel)
        if platform is not None:
            query = query.where(Channel.platform == platform)

        result = await self.session.execute(query)
        channels = result.scalars().all()

        if not channels:
            return []

        channel_ids = [ch.id for ch in channels]

        uc_query = select(UserChannel).where(
            and_(
                UserChannel.user_id == user_id, UserChannel.channel_id.in_(channel_ids)
            )
        )
        uc_result = await self.session.execute(uc_query)
        status_map = {uc.channel_id: uc.status for uc in uc_result.scalars().all()}

        return [(ch, status_map.get(ch.id)) for ch in channels]


class UserChannelRepository(CRUDBase[UserChannel]):
    """用户-频道关联的 Repository。"""

    def __init__(self, session: AsyncSession):
        super().__init__(UserChannel, session)

    async def get_by_user_and_channel(
        self, user_id: int, channel_id: int
    ) -> Optional[UserChannel]:
        """获取用户对特定频道的关注状态。"""
        query = select(UserChannel).where(
            and_(UserChannel.user_id == user_id, UserChannel.channel_id == channel_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_liked_channels(self, user_id: int) -> list[Channel]:
        """获取用户喜欢的频道列表。"""
        query = (
            select(Channel)
            .join(UserChannel, UserChannel.channel_id == Channel.id)
            .where(and_(UserChannel.user_id == user_id, UserChannel.status == "liked"))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_user_blocked_channels(self, user_id: int) -> list[Channel]:
        """获取用户屏蔽的频道列表。"""
        query = (
            select(Channel)
            .join(UserChannel, UserChannel.channel_id == Channel.id)
            .where(
                and_(UserChannel.user_id == user_id, UserChannel.status == "blocked")
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def set_status(
        self, user_id: int, channel_id: int, status: str
    ) -> UserChannel:
        """设置用户对频道的关注状态。"""
        existing = await self.get_by_user_and_channel(user_id, channel_id)
        if existing:
            existing.status = status
            await self.session.flush()
            return existing

        uc = UserChannel(user_id=user_id, channel_id=channel_id, status=status)
        self.session.add(uc)
        await self.session.flush()
        return uc

    async def remove_status(self, user_id: int, channel_id: int) -> bool:
        """移除用户对频道的关注状态。"""
        existing = await self.get_by_user_and_channel(user_id, channel_id)
        if existing:
            await self.session.delete(existing)
            await self.session.flush()
            return True
        return False


class OrganizationRepository(CRUDBase[Organization]):
    """组织实体的 Repository。"""

    def __init__(self, session: AsyncSession):
        super().__init__(Organization, session)

    async def get_by_name(self, name: str) -> Optional[Organization]:
        """通过名称查询。"""
        return await self.get_by_column(name=name)

    async def get_with_channels(self, org_id: int) -> Optional[Organization]:
        """获取组织及其关联的 Channel 列表。"""
        query = (
            select(Organization)
            .options(selectinload(Organization.channels))
            .where(Organization.id == org_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all_with_channel_count(self) -> list[tuple[Organization, int]]:
        """获取所有组织及其频道数量。"""
        query = select(Organization)
        result = await self.session.execute(query)
        orgs = result.scalars().all()

        result_list = []
        for org in orgs:
            count_query = (
                select(func.count())
                .select_from(Channel)
                .where(Channel.org_id == org.id)
            )
            count_result = await self.session.execute(count_query)
            count = count_result.scalar() or 0
            result_list.append((org, count))

        return result_list
