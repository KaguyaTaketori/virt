from __future__ import annotations

from app.repositories.channels import (
    ChannelRepository,
    UserChannelRepository,
    OrganizationRepository,
)
from app.repositories.videos import VideoRepository
from app.repositories.streams import StreamRepository
from app.repositories.bilibili_dynamics import BilibiliDynamicRepository
from app.repositories.users import UserRepository
from app.repositories.roles import RoleRepository
from app.repositories.permissions import PermissionRepository
from app.repositories.user_roles import UserRoleRepository
from app.repositories.role_permissions import RolePermissionRepository
from app.repositories.resource_acls import ResourceACLRepository

__all__ = [
    "ChannelRepository",
    "UserChannelRepository",
    "OrganizationRepository",
    "VideoRepository",
    "StreamRepository",
    "BilibiliDynamicRepository",
    "UserRepository",
    "RoleRepository",
    "PermissionRepository",
    "UserRoleRepository",
    "RolePermissionRepository",
    "ResourceACLRepository",
]
