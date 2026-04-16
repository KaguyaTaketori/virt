from __future__ import annotations

from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import BaseRepository
from app.models.models import UserRole, Role


class UserRoleRepository(BaseRepository[UserRole]):
    """UserRole 实体的 Repository。"""

    model = UserRole

    async def get_by_user_id(self, user_id: int) -> list[UserRole]:
        """获取用户所有角色关联。"""
        query = select(UserRole).where(UserRole.user_id == user_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete_by_user_id(self, user_id: int) -> int:
        """删除用户所有角色关联，返回删除数量。"""
        query = delete(UserRole).where(UserRole.user_id == user_id)
        result = await self.session.execute(query)
        return result.rowcount

    async def assign_roles(
        self,
        user_id: int,
        role_ids: list[int],
    ) -> list[UserRole]:
        """批量分配角色给用户。"""
        await self.delete_by_user_id(user_id)

        user_roles = []
        for role_id in role_ids:
            ur = UserRole(user_id=user_id, role_id=role_id)
            self.session.add(ur)
            user_roles.append(ur)

        await self.session.flush()
        return user_roles
