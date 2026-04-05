from __future__ import annotations

from typing import Callable, Optional
from functools import wraps

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select

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


async def get_user_roles(user_id: int, db: AsyncSession) -> set[str]:
    """返回用户所有角色名称集合。"""
    stmt = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    result = await db.execute(stmt)
    return set(result.scalars().all())


async def has_role(user_id: int, role_name: str, db: AsyncSession) -> bool:
    roles = await get_user_roles(user_id, db)
    return role_name in roles


async def has_permission(
    user_id: int,
    resource: str,
    action: str,
    db: AsyncSession,
    resource_id: Optional[int] = None,
) -> bool:
    roles = await get_user_roles(user_id, db)
    if "superadmin" in roles:
        return True

    stmt = (
        select(1)
        .select_from(RolePermission)
        .join(Permission)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(
            UserRole.user_id == user_id,
            Permission.resource == resource,
            Permission.action == action,
        )
        .limit(1)
    )
    if (await db.execute(stmt)).scalar_one_or_none():
        return True

    if resource_id is not None:
        acl_stmt = (
            select(1)
            .select_from(ResourceACL)
            .where(
                ResourceACL.user_id == user_id,
                ResourceACL.resource == resource,
                ResourceACL.resource_id == resource_id,
                ResourceACL.access.in_(["owner", "editor"]),
            )
            .limit(1)
        )
        if (await db.execute(acl_stmt)).scalar_one_or_none():
            return True

    return False


async def assign_role(user_id: int, role_id: int, db: AsyncSession) -> None:
    stmt = select(UserRole).where(
        UserRole.user_id == user_id, UserRole.role_id == role_id
    )
    if not (await db.execute(stmt)).scalar_one_or_none():
        db.add(UserRole(user_id=user_id, role_id=role_id))
        await db.commit()


async def remove_role(user_id: int, role_id: int, db: AsyncSession) -> None:
    stmt = delete(UserRole).where(
        UserRole.user_id == user_id, UserRole.role_id == role_id
    )
    await db.execute(stmt)
    await db.commit()


async def verify_ownership(
    user_id: int, resource: str, resource_id: int, db: AsyncSession
) -> bool:
    roles = await get_user_roles(user_id, db)
    if "superadmin" in roles or "admin" in roles:
        return True

    stmt = (
        select(1)
        .select_from(ResourceACL)
        .where(
            ResourceACL.user_id == user_id,
            ResourceACL.resource == resource,
            ResourceACL.resource_id == resource_id,
        )
        .limit(1)
    )

    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def get_all_permissions_for_user(user_id: int, db: AsyncSession) -> list[dict]:
    """获取用户所有权限列表，返回 [{resource, action}, ...]。"""
    roles = await get_user_roles(user_id, db)
    if "superadmin" in roles:
        result = await db.execute(select(Permission))
        return [
            {"resource": p.resource, "action": p.action} for p in result.scalars().all()
        ]

    stmt = (
        select(Permission.resource, Permission.action)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user_id)
        .distinct()
    )
    result = await db.execute(stmt)
    return [{"resource": r.resource, "action": r.action} for r in result.all()]
