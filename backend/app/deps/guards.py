from __future__ import annotations

from typing import Callable, Optional
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_optional, get_current_user
from app.deps.base import get_async_db
from app.models.models import User
from app.services.permissions import get_user_roles, has_permission


class _PermissionGuard:
    __slots__ = ("resource", "action", "require", "allow_anonymous")

    def __init__(
        self,
        resource: str,
        action: str,
        *,
        require: bool = True,
        allow_anonymous: bool = False,
    ) -> None:
        self.resource = resource
        self.action = action
        self.require = require
        self.allow_anonymous = allow_anonymous

    async def __call__(
        self,
        db: AsyncSession = Depends(get_async_db),
        current_user: Optional[User] = Depends(get_current_user_optional),
    ) -> bool | User:
        if current_user is None:
            if not self.require and self.allow_anonymous:
                return False
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        granted = await has_permission(current_user.id, self.resource, self.action, db)

        if self.require:
            if not granted:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission required: {self.resource}.{self.action}",
                )
            return current_user

        return granted



def require_permission(resource: str, action: str) -> _PermissionGuard:
    return _PermissionGuard(resource, action, require=True, allow_anonymous=False)


def soft_permission(resource: str, action: str) -> _PermissionGuard:
    return _PermissionGuard(resource, action, require=False, allow_anonymous=True)

def require_roles(*allowed_roles: str) -> Callable:
    async def _dependency(
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_roles = await get_user_roles(current_user.id, db)
        
        if "superadmin" in user_roles:
            return current_user
            
        if not user_roles.intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Require one of roles: {', '.join(allowed_roles)}",
            )
        return current_user

    return _dependency

AdminUser = Depends(require_roles("admin", "superadmin"))
SuperAdminUser = Depends(require_roles("superadmin"))
AnyAuthUser = Depends(get_current_user)

AdminAccess = Depends(require_permission("system", "manage"))
BilibiliRequired = Depends(require_permission("bilibili", "access"))
BilibiliAccess = Depends(soft_permission("bilibili", "access"))
WebSubManage = Depends(require_permission("websub", "manage"))
ChannelManage = Depends(require_permission("channel", "manage"))

def validate_websub_callback(callback_url: str, allowed_callback_url: str) -> str:
    try:
        given_host = urlparse(callback_url).hostname
        allowed_host = urlparse(allowed_callback_url).hostname
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid callback URL format")

    if not given_host or given_host != allowed_host:
        raise HTTPException(
            status_code=400,
            detail=f"Callback URL must be on the same host as configured: {allowed_host}",
        )
    return callback_url