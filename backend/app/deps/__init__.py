from __future__ import annotations

from app.deps.base import get_db_session
from app.deps.permissions import (
    PermissionDep,
    QuotaDep,
    init_deps,
    get_permission_dep,
    get_quota_dep,
    require_quota,
)
from app.deps.guards import (
    AuthContext,
    require_permission,
    soft_permission,
    require_roles,
    AdminUser,
    SuperAdminUser,
    AnyAuthUser,
    AdminManage,
    BilibiliRequired,
    BilibiliAccess,
    WebSubManage,
    ChannelManage,
    validate_websub_callback,
)
from app.deps.platform_guard import PlatformContext, PlatformGuardDep

__all__ = [
    "get_db_session",
    "PermissionDep",
    "QuotaDep",
    "init_deps",
    "get_permission_dep",
    "get_quota_dep",
    "require_quota",
    "AuthContext",
    "require_permission",
    "soft_permission",
    "require_roles",
    "AdminUser",
    "SuperAdminUser",
    "AnyAuthUser",
    "AdminManage",
    "BilibiliRequired",
    "BilibiliAccess",
    "WebSubManage",
    "ChannelManage",
    "validate_websub_callback",
    "PlatformContext",
    "PlatformGuardDep",
]
