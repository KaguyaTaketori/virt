from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import get_db
from app.models.models import Role, User, UserRole
from app.services.permissions import has_permission


# ── 内部工具 ──────────────────────────────────────────────────────────────────
def _get_user_role_names(user_id: int, db: Session) -> set[str]:
    user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    if not user_roles:
        return set()
    role_ids = [ur.role_id for ur in user_roles]
    roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
    return {r.name for r in roles}


# ── 公开工厂函数 ──────────────────────────────────────────────────────────────
def require_roles(*allowed_roles: str) -> Callable:
    """
    要求当前用户拥有指定角色之一（superadmin 始终放行）。

    用法 A — 仅校验，不需要用户对象：
        @router.post("", dependencies=[Depends(require_roles("admin", "superadmin"))])

    用法 B — 校验同时获取用户对象：
        @router.delete("/{id}")
        def delete_item(current_user: User = Depends(require_roles("admin"))):
            ...
    """
    def _dependency(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_role_names = _get_user_role_names(current_user.id, db)
        if "superadmin" in user_role_names:
            return current_user
        if not user_role_names.intersection(set(allowed_roles)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要以下角色之一: {', '.join(allowed_roles)}",
            )
        return current_user

    return _dependency


def require_permission_dep(resource: str, action: str) -> Callable:
    """
    要求当前用户拥有特定资源权限。

    用法：
        @router.post("/scrape/all",
            dependencies=[Depends(require_permission_dep("channel", "manage"))])
    """
    def _dependency(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not has_permission(current_user.id, resource, action, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {resource}.{action}",
            )
        return current_user

    return _dependency


AdminUser = Depends(require_roles("admin", "superadmin"))
SuperAdminUser = Depends(require_roles("superadmin"))
AnyAuthUser = Depends(get_current_user)