from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from app.database.base import BaseRepository
from app.models.models import ResourceACL


class ResourceACLRepository(BaseRepository[ResourceACL]):
    """ResourceACL 实体的 Repository。"""

    model = ResourceACL

    async def get_by_user_and_resource(
        self,
        user_id: int,
        resource: str,
        resource_id: int,
    ) -> Optional[ResourceACL]:
        """通过用户+资源组合查询。"""
        query = select(ResourceACL).where(
            ResourceACL.user_id == user_id,
            ResourceACL.resource == resource,
            ResourceACL.resource_id == resource_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def upsert_or_update(
        self,
        user_id: int,
        resource: str,
        resource_id: int,
        access: str,
    ) -> tuple[ResourceACL, bool]:
        """插入或更新资源ACL。"""
        existing = await self.get_by_user_and_resource(user_id, resource, resource_id)

        if existing:
            existing.access = access
            await self.session.flush()
            return existing, False

        acl = ResourceACL(
            user_id=user_id,
            resource=resource,
            resource_id=resource_id,
            access=access,
        )
        self.session.add(acl)
        await self.session.flush()
        return acl, True
