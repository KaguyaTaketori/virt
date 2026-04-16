from __future__ import annotations

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import BaseRepository
from app.models.models import Permission, RolePermission, UserRole


class PermissionRepository(BaseRepository[Permission]):
    """Permission 实体的 Repository。"""

    model = Permission

    async def get_by_id(self, permission_id: int) -> Optional[Permission]:
        """通过ID查询。"""
        return await self.get(permission_id)

    async def get_all(self) -> list[Permission]:
        """获取所有权限。"""
        return await self.get_multi()

    async def get_all_names(self) -> list[str]:
        """获取所有权限名称（用于 SUPERADMIN）。"""
        query = select(Permission.name)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all_names_for_user(self, user_id: int) -> list[str]:
        """获取用户所有权限名称（通过角色链式查询）。"""
        query = (
            select(Permission.name)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .join(UserRole, RolePermission.role_id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
            .distinct()
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
