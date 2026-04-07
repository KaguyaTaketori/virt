from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.deps import get_db_session
from app.models.models import (
    User,
    Role,
    Permission,
    UserRole,
    RolePermission,
    ResourceACL,
)
from app.schemas.schemas import (
    RoleResponse,
    PermissionResponse,
    UserResponse,
    UserRoleUpdate,
)
from app.auth import get_current_user
from app.services.permissions import get_user_roles, has_permission
from app.deps.guards import AdminUser, SuperAdminUser
from app.services.permission_cache import permission_cache

router = APIRouter(prefix="/api/admin/permissions", tags=["permissions"])


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    resp = UserResponse.model_validate(current_user)
    resp.roles = await get_user_roles(current_user.id, db)

    if "superadmin" in resp.roles:
        result = await db.execute(select(Permission.name))
        resp.permissions = list(result.scalars().all())
        return resp

    result = await db.execute(
        select(Permission.name)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .join(UserRole, RolePermission.role_id == UserRole.role_id)
        .where(UserRole.user_id == current_user.id)
        .distinct()
    )
    resp.permissions = list(result.scalars().all())
    return resp


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db_session),
    _: User = SuperAdminUser,
):
    result = await db.execute(select(Role))
    return result.scalars().all()


@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role: RoleResponse,
    db: AsyncSession = Depends(get_db_session),
    _: User = SuperAdminUser,
):
    result = await db.execute(select(Role).where(Role.name == role.name))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Role already exists")

    db_role = Role(name=role.name, description=role.description)
    db.add(db_role)
    await db.commit()
    await db.refresh(db_role)
    return db_role


@router.get("/roles/{role_id}/permissions", response_model=List[int])
async def get_role_permissions(
    role_id: int,
    db: AsyncSession = Depends(get_db_session),
    _: User = AdminUser,
):
    """获取角色已分配的权限ID列表"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    result = await db.execute(
        select(RolePermission).where(RolePermission.role_id == role_id)
    )
    perms = result.scalars().all()
    return [rp.permission_id for rp in perms]


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    db: AsyncSession = Depends(get_db_session),
    _: User = AdminUser,
):
    result = await db.execute(select(Permission))
    return result.scalars().all()


@router.post("/permissions", response_model=PermissionResponse)
async def create_permission(
    permission: PermissionResponse,
    db: AsyncSession = Depends(get_db_session),
    _: User = SuperAdminUser,
):
    result = await db.execute(
        select(Permission).where(Permission.name == permission.name)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Permission already exists")

    db_perm = Permission(
        name=permission.name,
        description=permission.description,
        resource=permission.resource,
        action=permission.action,
    )
    db.add(db_perm)
    await db.commit()
    await db.refresh(db_perm)
    return db_perm


@router.post("/roles/{role_id}/permissions")
async def assign_permissions_to_role(
    role_id: int,
    permission_ids: List[int],
    db: AsyncSession = Depends(get_db_session),
    _: User = SuperAdminUser,
):
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    for perm_id in permission_ids:
        result = await db.execute(select(Permission).where(Permission.id == perm_id))
        perm = result.scalar_one_or_none()
        if not perm:
            continue

        result = await db.execute(
            select(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == perm_id,
            )
        )
        existing = result.scalar_one_or_none()

        if not existing:
            rp = RolePermission(role_id=role_id, permission_id=perm_id)
            db.add(rp)

    await db.commit()
    await permission_cache.delete_all()
    return {"message": "Permissions assigned"}


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = Query(default=100, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    _: User = AdminUser,
):
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()

    user_ids = [u.id for u in users]
    roles_result = await db.execute(
        select(UserRole.user_id, Role.name)
        .join(Role, UserRole.role_id == Role.id)
        .where(UserRole.user_id.in_(user_ids))
    )
    user_roles_map: dict[int, list[str]] = {}
    for user_id, role_name in roles_result.all():
        user_roles_map.setdefault(user_id, []).append(role_name)

    result_list = []
    for user in users:
        resp = UserResponse.model_validate(user)
        resp.roles = user_roles_map.get(user.id, [])
        result_list.append(resp)
    return result_list


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db_session),
    _: User = AdminUser,
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    resp = UserResponse.model_validate(user)
    resp.roles = await get_user_roles(user.id, db)
    return resp


@router.put("/users/{user_id}/roles")
async def update_user_roles(
    user_id: int,
    role_update: UserRoleUpdate,
    db: AsyncSession = Depends(get_db_session),
    _: User = SuperAdminUser,
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(UserRole).where(UserRole.user_id == user_id))
    for er in result.scalars().all():
        await db.delete(er)

    for role_id in role_update.role_ids:
        result = await db.execute(select(Role).where(Role.id == role_id))
        role = result.scalar_one_or_none()
        if role:
            ur = UserRole(user_id=user_id, role_id=role_id)
            db.add(ur)

    await db.commit()
    await permission_cache.delete_all_by_user(user_id)
    return {"message": "Roles updated"}


@router.post("/users/{user_id}/resource-acl")
async def create_resource_acl(
    user_id: int,
    resource: str,
    resource_id: int,
    access: str,
    db: AsyncSession = Depends(get_db_session),
    _: User = AdminUser,
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(ResourceACL).where(
            ResourceACL.user_id == user_id,
            ResourceACL.resource == resource,
            ResourceACL.resource_id == resource_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.access = access
    else:
        acl = ResourceACL(
            user_id=user_id, resource=resource, resource_id=resource_id, access=access
        )
        db.add(acl)

    await db.commit()
    return {"message": "Resource ACL created/updated"}


@router.delete("/resource-acl/{acl_id}")
async def delete_resource_acl(
    acl_id: int,
    db: AsyncSession = Depends(get_db_session),
    _: User = AdminUser,
):
    result = await db.execute(select(ResourceACL).where(ResourceACL.id == acl_id))
    acl = result.scalar_one_or_none()
    if not acl:
        raise HTTPException(status_code=404, detail="ACL not found")

    await db.delete(acl)
    await db.commit()
    return {"message": "ACL deleted"}
