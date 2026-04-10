# backend/app/deps/platform_guard.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.base import get_db_session
from app.models.models import Platform, User
from app.auth import get_current_user_optional
from app.services.permissions import has_permission
from app.constants import PermissionAction, PermissionResource


@dataclass(frozen=True, slots=True)
class PlatformContext:
    """封装当前请求的平台访问上下文，供所有路由统一使用"""

    current_user: Optional[User]
    can_bilibili: bool
    can_youtube: bool = True  # YouTube 始终公开

    @property
    def user_id(self) -> Optional[int]:
        """便捷获取 user_id，避免层层判空"""
        return self.current_user.id if self.current_user else None

    @property
    def allowed_platforms(self) -> list[str]:
        """
        动态计算当前用户被允许访问的平台列表（字符串值）。
        未来如果增加 Twitch 或其他平台，只需在这里添加逻辑即可，无需修改任何业务路由！
        """
        platforms = [Platform.YOUTUBE.value]  # 所有人默认可访问
        if self.can_bilibili:
            platforms.append(Platform.BILIBILI.value)
        return platforms

    def is_platform_allowed(self, platform: Platform | str) -> bool:
        """在 Python 内存级别验证单条数据/参数的平台权限"""
        platform_str = platform.value if isinstance(platform, Platform) else platform
        return platform_str in self.allowed_platforms

    def apply_platform_filter(self, query: Select, platform_column) -> Select:
        """
        将平台过滤条件统一应用到 ORM 查询 (SQL 级别)。
        使用 IN 子句而不是等于/不等于，完美支持多平台扩展。
        """
        if len(self.allowed_platforms) == len(Platform):
            return query

        return query.where(platform_column.in_(self.allowed_platforms))

    def assert_platform_access(self, platform: Platform | str) -> None:
        """
        通用断言：检查并抛出对应平台的权限异常 (Python 级别拦截)。
        """
        if self.is_platform_allowed(platform):
            return

        if self.current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="此功能需要登录",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"没有访问 {platform} 平台的权限",
        )

    def assert_bilibili_access(self) -> None:
        """保留这个快捷方法，因为它是目前最常用的特殊断言"""
        self.assert_platform_access(Platform.BILIBILI)


async def _build_platform_context(
    db: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> PlatformContext:
    """构建权限上下文"""
    can_bilibili = False
    if current_user is not None:
        can_bilibili = await has_permission(current_user.id, PermissionResource.BILIBILI, PermissionAction.ACCESS, db)

    return PlatformContext(
        current_user=current_user,
        can_bilibili=can_bilibili,
    )


PlatformGuardDep = Depends(_build_platform_context)
