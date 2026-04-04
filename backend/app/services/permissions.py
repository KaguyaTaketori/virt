from __future__ import annotations

from typing import Callable, Optional
from functools import wraps

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.deps import get_async_db
from app.models.models import (
    User,
    Role,
    Permission,
    UserRole,
    RolePermission,
    ResourceACL,
)
from app.auth import get_current_user_optional


async def get_user_roles(user_id: int, db: AsyncSession) -> list[str]:
    """返回用户所有角色名称列表。"""
    result = await db.execute(select(UserRole).where(UserRole.user_id == user_id))
    role_ids = [ur.role_id for ur in result.scalars().all()]
    if not role_ids:
        return []
    result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
    roles = result.scalars().all()
    return [r.name for r in roles]


async def has_role(user_id: int, role_name: str, db: AsyncSession) -> bool:
    result = await db.execute(select(UserRole).where(UserRole.user_id == user_id))
    role_ids = [ur.role_id for ur in result.scalars().all()]
    if not role_ids:
        return False
    result = await db.execute(
        select(Role).where(Role.id.in_(role_ids), Role.name == role_name)
    )
    return result.scalar_one_or_none() is not None


async def has_permission(
    user_id: int, resource: str, action: str, db: AsyncSession
) -> bool:
    if await has_role(user_id, "superadmin", db):
        return True
    result = await db.execute(select(UserRole).where(UserRole.user_id == user_id))
    role_ids = [ur.role_id for ur in result.scalars().all()]
    if not role_ids:
        return False
    result = await db.execute(
        select(RolePermission)
        .join(Permission)
        .where(
            RolePermission.role_id.in_(role_ids),
            Permission.resource == resource,
            Permission.action == action,
        )
    )
    return result.scalar_one_or_none() is not None


async def assign_role(user_id: int, role_id: int, db: AsyncSession) -> None:
    result = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    )
    exists = result.scalar_one_or_none()
    if not exists:
        db.add(UserRole(user_id=user_id, role_id=role_id))
        await db.commit()


async def remove_role(user_id: int, role_id: int, db: AsyncSession) -> None:
    await db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    )
    await db.execute(
        (await db.connection()).exec_driver_sql(
            f"DELETE FROM user_roles WHERE user_id = {user_id} AND role_id = {role_id}"
        )
    )
    await db.commit()


class PermissionChecker:
    """用法：Depends(PermissionChecker('channel', 'manage'))"""

    def __init__(self, resource: str, action: str, resource_id: Optional[int] = None):
        self.resource = resource
        self.action = action
        self.resource_id = resource_id

    async def __call__(
        self,
        current_user: Optional[User] = Depends(get_current_user_optional),
        db: AsyncSession = Depends(get_async_db),
    ) -> User:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        if not await self._check(db, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {self.resource}.{self.action}",
            )
        return current_user

    async def _check(self, db: AsyncSession, user_id: int) -> bool:
        if await has_role(user_id, "superadmin", db):
            return True
        result = await db.execute(select(UserRole).where(UserRole.user_id == user_id))
        role_ids = [ur.role_id for ur in result.scalars().all()]
        if not role_ids:
            return False
        result = await db.execute(
            select(RolePermission)
            .join(Permission)
            .where(
                RolePermission.role_id.in_(role_ids),
                Permission.resource == self.resource,
                Permission.action == self.action,
            )
        )
        has_perm = result.scalar_one_or_none()
        if has_perm:
            return True
        if self.resource_id:
            result = await db.execute(
                select(ResourceACL).where(
                    ResourceACL.user_id == user_id,
                    ResourceACL.resource == self.resource,
                    ResourceACL.resource_id == self.resource_id,
                    ResourceACL.access.in_(["owner", "editor"]),
                )
            )
            acl = result.scalar_one_or_none()
            if acl:
                return True
        return False


class OwnershipVerifier:
    @staticmethod
    async def verify(
        user_id: int, resource: str, resource_id: int, db: AsyncSession
    ) -> bool:
        result = await db.execute(
            select(ResourceACL).where(
                ResourceACL.user_id == user_id,
                ResourceACL.resource == resource,
                ResourceACL.resource_id == resource_id,
            )
        )
        acl = result.scalar_one_or_none()
        if acl:
            return True
        roles = await get_user_roles(user_id, db)
        return any(r in roles for r in ("superadmin", "admin"))

    @staticmethod
    async def require(
        user_id: int, resource: str, resource_id: int, db: AsyncSession
    ) -> None:
        if not await OwnershipVerifier.verify(user_id, resource, resource_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to {resource}:{resource_id}",
            )


def require_permission(resource: str, action: str):
    """用法：@require_permission('channel', 'manage')"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            db: AsyncSession = kwargs.get("db")
            current_user: Optional[User] = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )
            checker = PermissionChecker(resource, action)
            if not await checker._check(db, current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {resource}.{action}",
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator
