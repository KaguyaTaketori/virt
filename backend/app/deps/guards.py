from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_optional, get_current_user
from app.deps.base import get_async_db
from app.models.models import User
from app.services.permissions import has_permission, has_role


# ── 核心：可组合的权限依赖工厂 ─────────────────────────────────────────────────
class _PermissionGuard:
    """
    通用权限 Dependency，支持软/硬两种模式。

    参数：
      resource        权限资源（如 "bilibili", "channel", "websub"）
      action          权限操作（如 "access", "manage"）
      require         True  → 无权限抛 403（强制模式，返回 User）
                      False → 无权限返回 False（软模式，返回 bool）
      allow_anonymous True  → 未登录时软模式返回 False，不抛 401
                      False → 未登录时强制模式抛 401
    """

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
        # ── 匿名用户 ──────────────────────────────────────────────────────────
        if current_user is None:
            if not self.require and self.allow_anonymous:
                return False
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # ── superadmin 始终放行（has_permission 内部已处理，此处提前短路节省 DB 查询）
        if await has_role(current_user.id, "superadmin", db):
            return current_user if self.require else True

        # ── 普通权限检查 ───────────────────────────────────────────────────────
        granted = await has_permission(current_user.id, self.resource, self.action, db)

        if self.require:
            if not granted:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission required: {self.resource}.{self.action}",
                )
            return current_user

        return granted  # 软模式直接返回 bool


def require_permission(resource: str, action: str) -> _PermissionGuard:
    """
    强制权限依赖（未登录 401，无权限 403）。
    返回 User 对象，可在路由参数中使用。

    示例：
        @router.post("/foo")
        async def endpoint(user: User = Depends(require_permission("channel", "manage"))):
            ...
    """
    return _PermissionGuard(resource, action, require=True, allow_anonymous=False)


def soft_permission(resource: str, action: str) -> _PermissionGuard:
    """
    软权限依赖（未登录/无权限都返回 False，不抛异常）。
    用于"有权限看更多，无权限看部分"的数据过滤场景。

    示例：
        @router.get("/channels")
        async def get_channels(can_bilibili: bool = Depends(soft_permission("bilibili", "access"))):
            if not can_bilibili:
                query = query.where(Channel.platform == "youtube")
    """
    return _PermissionGuard(resource, action, require=False, allow_anonymous=True)


# ── 预定义常用 Guards（项目级复用）──────────────────────────────────────────────

# [强制] 管理员操作
AdminAccess = Depends(require_permission("system", "manage"))

# [强制] Bilibili 访问（需登录 + 有权限）
BilibiliRequired = Depends(require_permission("bilibili", "access"))

# [软] Bilibili 访问（未登录/无权限返回 False，用于数据过滤）
BilibiliAccess = Depends(soft_permission("bilibili", "access"))

# [强制] WebSub 管理（修复致命漏洞：websub 端点无鉴权）
WebSubManage = Depends(require_permission("websub", "manage"))

# [强制] 频道管理
ChannelManage = Depends(require_permission("channel", "manage"))


# ── WebSub callback URL 白名单校验（防 SSRF via WebSub）──────────────────────
def validate_websub_callback(callback_url: str, allowed_callback_url: str) -> str:
    """
    校验 WebSub 回调 URL 必须与配置的域名一致，防止攻击者注入任意内网地址。
    使用方式：在 websub 路由中调用此函数。
    """
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