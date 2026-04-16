from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from app.database.base import BaseRepository
from app.models.models import Role


class RoleRepository(BaseRepository[Role]):
    """Role 实体的 Repository。"""

    model = Role

    async def get_by_name(self, name: str) -> Optional[Role]:
        """通过名称查询。"""
        return await self.get_by_column(name=name)

    async def get_all(self) -> list[Role]:
        """获取所有角色。"""
        return await self.get_multi()
