from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.repositories import (
    ChannelRepository,
    UserChannelRepository,
    OrganizationRepository,
    VideoRepository,
    StreamRepository,
    BilibiliDynamicRepository,
    UserRepository,
    RoleRepository,
    PermissionRepository,
    UserRoleRepository,
    RolePermissionRepository,
    ResourceACLRepository,
)


async def get_channel_repo(
    db: AsyncSession = Depends(get_db_session),
) -> ChannelRepository:
    return ChannelRepository(db)


async def get_user_channel_repo(
    db: AsyncSession = Depends(get_db_session),
) -> UserChannelRepository:
    return UserChannelRepository(db)


async def get_organization_repo(
    db: AsyncSession = Depends(get_db_session),
) -> OrganizationRepository:
    return OrganizationRepository(db)


async def get_video_repo(
    db: AsyncSession = Depends(get_db_session),
) -> VideoRepository:
    return VideoRepository(db)


async def get_stream_repo(
    db: AsyncSession = Depends(get_db_session),
) -> StreamRepository:
    return StreamRepository(db)


async def get_bilibili_dynamic_repo(
    db: AsyncSession = Depends(get_db_session),
) -> BilibiliDynamicRepository:
    return BilibiliDynamicRepository(db)


async def get_user_repo(
    db: AsyncSession = Depends(get_db_session),
) -> UserRepository:
    return UserRepository(db)


async def get_role_repo(
    db: AsyncSession = Depends(get_db_session),
) -> RoleRepository:
    return RoleRepository(db)


async def get_permission_repo(
    db: AsyncSession = Depends(get_db_session),
) -> PermissionRepository:
    return PermissionRepository(db)


async def get_user_role_repo(
    db: AsyncSession = Depends(get_db_session),
) -> UserRoleRepository:
    return UserRoleRepository(db)


async def get_role_permission_repo(
    db: AsyncSession = Depends(get_db_session),
) -> RolePermissionRepository:
    return RolePermissionRepository(db)


async def get_resource_acl_repo(
    db: AsyncSession = Depends(get_db_session),
) -> ResourceACLRepository:
    return ResourceACLRepository(db)
