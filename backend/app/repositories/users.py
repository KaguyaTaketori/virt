from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.base import BaseRepository
from app.models.models import User, UserRole


class UserRepository(BaseRepository[User]):
    """User 实体的 Repository。"""

    model = User

    async def get_by_username(self, username: str) -> Optional[User]:
        """通过用户名查询。"""
        return await self.get_by_column(username=username)

    async def get_by_email(self, email: str) -> Optional[User]:
        """通过邮箱查询。"""
        return await self.get_by_column(email=email)

    async def get_with_roles(self, user_id: int) -> Optional[User]:
        """通过ID查询并预加载用户角色。"""
        query = (
            select(User)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .where(User.id == user_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_multi_with_roles(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        """分页查询用户列表并预加载角色。"""
        query = (
            select(User)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().unique().all())
