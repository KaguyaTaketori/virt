from __future__ import annotations

from typing import Callable
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.auth import get_current_user
from app.deps.base import get_db_session
from app.models.models import User
from app.services.permissions import get_user_roles, has_permission
from app.services.permission_cache import permission_cache


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
        token: str = Depends(
            OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
        ),
        db: AsyncSession = Depends(get_db_session),
    ) -> bool | User:
        if not token:
            if not self.require and self.allow_anonymous:
                return False
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            from jose import jwt as jose_jwt

            payload = jose_jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            username: str = payload.get("sub")
            jti: str = payload.get("jti", "")
            token_exp: int = payload.get("exp", 0)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        from app.services.token_blacklist import token_blacklist

        if jti and token_blacklist.is_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        result = await db.execute(select(User).where(User.username == username))
        current_user = result.scalar_one_or_none()
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        cached = await permission_cache.get_permissions(jti)
        if cached is not None:
            roles = set(cached.get("roles", []))
            if "superadmin" in roles:
                return current_user

            perms = cached.get("permissions", [])
            granted = any(
                p.get("resource") == self.resource and p.get("action") == self.action
                for p in perms
            )
            if self.require:
                if not granted:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission required: {self.resource}.{self.action}",
                    )
                return current_user
            return granted

        granted = await has_permission(current_user.id, self.resource, self.action, db)

        roles = await get_user_roles(current_user.id, db)
        from app.services.permissions import get_all_permissions_for_user

        perms = await get_all_permissions_for_user(current_user.id, db)
        if perms:
            await permission_cache.set_permissions(jti, roles, perms, token_exp)

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
        token: str = Depends(
            OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
        ),
        db: AsyncSession = Depends(get_db_session),
    ) -> User:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            from jose import jwt as jose_jwt

            payload = jose_jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            username: str = payload.get("sub")
            jti: str = payload.get("jti", "")
            token_exp: int = payload.get("exp", 0)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        from app.services.token_blacklist import token_blacklist

        if jti and token_blacklist.is_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        result = await db.execute(select(User).where(User.username == username))
        current_user = result.scalar_one_or_none()
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        cached = await permission_cache.get_permissions(jti)
        if cached is not None:
            roles = set(cached.get("roles", []))
        else:
            roles = await get_user_roles(current_user.id, db)
            from app.services.permissions import get_all_permissions_for_user

            perms = await get_all_permissions_for_user(current_user.id, db)
            if perms:
                await permission_cache.set_permissions(jti, roles, perms, token_exp)

        if "superadmin" in roles:
            return current_user

        if not roles.intersection(allowed_roles):
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
