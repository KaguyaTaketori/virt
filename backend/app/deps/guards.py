from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt as jose_jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.auth import get_current_user
from app.deps.base import get_db_session
from app.models.models import User
from app.services.permissions import get_user_roles, get_all_permissions_for_user
from app.services.permission_cache import get_permission_cache
from app.services.token_blacklist import token_blacklist
from app.constants import UserRole, PermissionResource, PermissionAction


@dataclass(frozen=True, slots=True)
class AuthContext:
    user: User
    jti: str
    token_exp: int
    roles: frozenset[str]
    permissions: list[dict]

    def has_role(self, *roles: str) -> bool:
        return bool(self.roles.intersection(roles))

    def has_permission(self, resource: str, action: str) -> bool:
        return UserRole.SUPERADMIN in self.roles or any(
            p.get("resource") == resource and p.get("action") == action
            for p in self.permissions
        )
    

_bearer = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def _resolve_auth_context(
    token: str,
    db: AsyncSession,
) -> AuthContext:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jose_jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: str | None = payload.get("sub")
    jti: str = payload.get("jti", "")
    token_exp: int = payload.get("exp", 0)

    if not username:
        raise HTTPException(status_code=401, detail="Could not validate credentials",
                            headers={"WWW-Authenticate": "Bearer"})

    if jti and token_blacklist.is_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found",
                            headers={"WWW-Authenticate": "Bearer"})

    cached = await get_permission_cache().get_permissions(jti, user.id)
    if cached is not None:
        return AuthContext(
            user=user,
            jti=jti,
            token_exp=token_exp,
            roles=frozenset(cached.get("roles", [])),
            permissions=cached.get("permissions", []),
        )

    roles = await get_user_roles(user.id, db)
    permissions = await get_all_permissions_for_user(user.id, db)
    if permissions:
        await get_permission_cache().set_permissions(jti, roles, permissions, token_exp, user.id)

    return AuthContext(
        user=user,
        jti=jti,
        token_exp=token_exp,
        roles=frozenset(roles),
        permissions=permissions,
    )


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
        token: str = Depends(_bearer),
        db: AsyncSession = Depends(get_db_session),
    ) -> bool | User:
        if not token:
            if not self.require and self.allow_anonymous:
                return False
            raise HTTPException(status_code=401, detail="Authentication required",
                                headers={"WWW-Authenticate": "Bearer"})

        ctx = await _resolve_auth_context(token, db)

        if ctx.has_role(UserRole.SUPERADMIN):
            return ctx.user

        granted = ctx.has_permission(self.resource, self.action)

        if self.require and not granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {self.resource}.{self.action}",
            )
        return ctx.user if granted else False

def require_permission(resource: str, action: str) -> _PermissionGuard:
    return _PermissionGuard(resource, action, require=True, allow_anonymous=False)


def soft_permission(resource: str, action: str) -> _PermissionGuard:
    return _PermissionGuard(resource, action, require=False, allow_anonymous=True)


def require_roles(*allowed_roles: str) -> Callable:
    async def _dependency(
        token: str = Depends(_bearer),
        db: AsyncSession = Depends(get_db_session),
    ) -> User:
        ctx = await _resolve_auth_context(token, db)

        if ctx.has_role(UserRole.SUPERADMIN) or ctx.has_role(*allowed_roles):
            return ctx.user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Require one of roles: {', '.join(allowed_roles)}",
        )
    return _dependency

AdminUser = Depends(require_roles(UserRole.ADMIN, UserRole.SUPERADMIN))
SuperAdminUser = Depends(require_roles(UserRole.SUPERADMIN))
AnyAuthUser = Depends(get_current_user)

AdminManage = Depends(require_permission(PermissionResource.SYSTEM, PermissionAction.MANAGE))
BilibiliRequired = Depends(require_permission(PermissionResource.BILIBILI, PermissionAction.ACCESS))
BilibiliAccess = Depends(soft_permission(PermissionResource.BILIBILI, PermissionAction.ACCESS))
WebSubManage = Depends(require_permission(PermissionResource.WEBSUB, PermissionAction.MANAGE))
ChannelManage = Depends(require_permission(PermissionResource.CHANNEL, PermissionAction.MANAGE))


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
