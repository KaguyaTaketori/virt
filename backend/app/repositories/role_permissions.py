from __future__ import annotations


from sqlalchemy import select

from app.database.base import BaseRepository
from app.models.models import RolePermission


class RolePermissionRepository(BaseRepository[RolePermission]):
    """RolePermission 实体的 Repository。"""

    model = RolePermission

    async def get_by_role_id(self, role_id: int) -> list[RolePermission]:
        """获取角色所有权限关联。"""
        query = select(RolePermission).where(RolePermission.role_id == role_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_permission_ids_by_role_id(self, role_id: int) -> list[int]:
        """获取角色所有权限ID列表。"""
        query = select(RolePermission.permission_id).where(
            RolePermission.role_id == role_id
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def exists(self, role_id: int, permission_id: int) -> bool:
        """检查角色-权限关联是否存在。"""
        query = select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def assign_permissions(
        self,
        role_id: int,
        permission_ids: list[int],
    ) -> list[RolePermission]:
        """批量分配权限给角色。"""
        role_permissions = []
        for perm_id in permission_ids:
            existing = await self.exists(role_id, perm_id)
            if not existing:
                rp = RolePermission(role_id=role_id, permission_id=perm_id)
                self.session.add(rp)
                role_permissions.append(rp)

        await self.session.flush()
        return role_permissions
