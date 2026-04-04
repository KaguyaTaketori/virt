from __future__ import annotations

from typing import Callable, Optional
from functools import wraps

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.models import (
    User,
    Role,
    Permission,
    UserRole,
    RolePermission,
    ResourceACL,
)
from app.auth import get_current_user_optional


# ── 基础查询工具 ──────────────────────────────────────────────────────────────


def get_user_roles(user_id: int, db: Session) -> list[str]:
    """返回用户所有角色名称列表。"""
    role_ids = [
        ur.role_id
        for ur in db.query(UserRole).filter(UserRole.user_id == user_id).all()
    ]
    if not role_ids:
        return []
    return [r.name for r in db.query(Role).filter(Role.id.in_(role_ids)).all()]


def has_role(user_id: int, role_name: str, db: Session) -> bool:
    role_ids = [
        ur.role_id
        for ur in db.query(UserRole).filter(UserRole.user_id == user_id).all()
    ]
    return bool(
        role_ids
        and db.query(Role).filter(Role.id.in_(role_ids), Role.name == role_name).first()
    )


def has_permission(user_id: int, resource: str, action: str, db: Session) -> bool:
    if has_role(user_id, "superadmin", db):
        return True
    role_ids = [
        ur.role_id
        for ur in db.query(UserRole).filter(UserRole.user_id == user_id).all()
    ]
    if not role_ids:
        return False
    return bool(
        db.query(RolePermission)
        .join(Permission)
        .filter(
            RolePermission.role_id.in_(role_ids),
            Permission.resource == resource,
            Permission.action == action,
        )
        .first()
    )


def assign_role(user_id: int, role_id: int, db: Session) -> None:
    exists = (
        db.query(UserRole)
        .filter(UserRole.user_id == user_id, UserRole.role_id == role_id)
        .first()
    )
    if not exists:
        db.add(UserRole(user_id=user_id, role_id=role_id))
        db.commit()


def remove_role(user_id: int, role_id: int, db: Session) -> None:
    db.query(UserRole).filter(
        UserRole.user_id == user_id, UserRole.role_id == role_id
    ).delete()
    db.commit()


# ── FastAPI Depends 风格的权限校验 ────────────────────────────────────────────
class PermissionChecker:
    """用法：Depends(PermissionChecker('channel', 'manage'))"""

    def __init__(self, resource: str, action: str, resource_id: Optional[int] = None):
        self.resource = resource
        self.action = action
        self.resource_id = resource_id

    def __call__(
        self,
        current_user: Optional[User] = Depends(get_current_user_optional),
        db: Session = Depends(get_db),
    ) -> User:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        if not self._check(db, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {self.resource}.{self.action}",
            )
        return current_user

    def _check(self, db: Session, user_id: int) -> bool:
        if has_role(user_id, "superadmin", db):
            return True
        role_ids = [
            ur.role_id
            for ur in db.query(UserRole).filter(UserRole.user_id == user_id).all()
        ]
        if not role_ids:
            return False
        has_perm = (
            db.query(RolePermission)
            .join(Permission)
            .filter(
                RolePermission.role_id.in_(role_ids),
                Permission.resource == self.resource,
                Permission.action == self.action,
            )
            .first()
        )
        if has_perm:
            return True
        if self.resource_id:
            acl = (
                db.query(ResourceACL)
                .filter(
                    ResourceACL.user_id == user_id,
                    ResourceACL.resource == self.resource,
                    ResourceACL.resource_id == self.resource_id,
                    ResourceACL.access.in_(["owner", "editor"]),
                )
                .first()
            )
            if acl:
                return True
        return False


# ── 所有权校验（防水平越权） ───────────────────────────────────────────────────


class OwnershipVerifier:
    @staticmethod
    def verify(user_id: int, resource: str, resource_id: int, db: Session) -> bool:
        acl = (
            db.query(ResourceACL)
            .filter(
                ResourceACL.user_id == user_id,
                ResourceACL.resource == resource,
                ResourceACL.resource_id == resource_id,
            )
            .first()
        )
        if acl:
            return True
        roles = get_user_roles(user_id, db)
        return any(r in roles for r in ("superadmin", "admin"))

    @staticmethod
    def require(user_id: int, resource: str, resource_id: int, db: Session) -> None:
        if not OwnershipVerifier.verify(user_id, resource, resource_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to {resource}:{resource_id}",
            )


def require_permission(resource: str, action: str):
    """用法：@require_permission('channel', 'manage')"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            db: Session = kwargs.get("db")
            current_user: Optional[User] = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )
            checker = PermissionChecker(resource, action)
            if not checker._check(db, current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {resource}.{action}",
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator
