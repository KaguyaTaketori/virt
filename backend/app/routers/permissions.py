from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.deps import (
    get_db_session,
    get_user_repo,
    get_role_repo,
    get_permission_repo,
    get_user_role_repo,
    get_role_permission_repo,
    get_resource_acl_repo,
)
from app.repositories import (
    UserRepository,
    RoleRepository,
    PermissionRepository,
    UserRoleRepository,
    RolePermissionRepository,
    ResourceACLRepository,
)
from app.models.models import User
from app.schemas.schemas import (
    RoleResponse,
    PermissionResponse,
    UserResponse,
    UserRoleUpdate,
)
from app.auth import get_current_user
from app.services.permissions import get_user_roles
from app.deps.guards import AdminUser, SuperAdminUser
from app.services.permission_cache import permission_cache
from app.constants import UserRole as UserRoleConstant

router = APIRouter(prefix="/api/admin/permissions", tags=["permissions"])


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    permission_repo: PermissionRepository = Depends(get_permission_repo),
):
    resp = UserResponse.model_validate(current_user)
    resp.roles = await get_user_roles(current_user.id, db)

    if UserRoleConstant.SUPERADMIN in resp.roles:
        resp.permissions = await permission_repo.get_all_names()
        return resp

    resp.permissions = await permission_repo.get_all_names_for_user(current_user.id)
    return resp


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    role_repo: RoleRepository = Depends(get_role_repo),
    _: User = SuperAdminUser,
):
    return await role_repo.get_all()


@router.post("/roles", response_model=RoleResponse, status_code=201)
async def create_role(
    role: RoleResponse,
    role_repo: RoleRepository = Depends(get_role_repo),
    _: User = SuperAdminUser,
):
    existing = await role_repo.get_by_name(role.name)
    if existing:
        raise HTTPException(status_code=409, detail="Role already exists")

    db_role = await role_repo.create({"name": role.name, "description": role.description})
    return db_role


@router.get("/roles/{role_id}/permissions", response_model=List[int])
async def get_role_permissions(
    role_id: int,
    role_repo: RoleRepository = Depends(get_role_repo),
    role_permission_repo: RolePermissionRepository = Depends(get_role_permission_repo),
    _: User = AdminUser,
):
    role = await role_repo.get(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    return await role_permission_repo.get_permission_ids_by_role_id(role_id)


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    permission_repo: PermissionRepository = Depends(get_permission_repo),
    _: User = AdminUser,
):
    return await permission_repo.get_all()


@router.post("/permissions", response_model=PermissionResponse)
async def create_permission(
    permission: PermissionResponse,
    permission_repo: PermissionRepository = Depends(get_permission_repo),
    _: User = SuperAdminUser,
):
    existing = await permission_repo.get_by_column(name=permission.name)
    if existing:
        raise HTTPException(status_code=400, detail="Permission already exists")

    return await permission_repo.create(
        {
            "name": permission.name,
            "description": permission.description,
            "resource": permission.resource,
            "action": permission.action,
        }
    )


@router.post("/roles/{role_id}/permissions")
async def assign_permissions_to_role(
    role_id: int,
    permission_ids: List[int],
    db: AsyncSession = Depends(get_db_session),
    role_repo: RoleRepository = Depends(get_role_repo),
    permission_repo: PermissionRepository = Depends(get_permission_repo),
    role_permission_repo: RolePermissionRepository = Depends(get_role_permission_repo),
    _: User = SuperAdminUser,
):
    role = await role_repo.get(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    for perm_id in permission_ids:
        perm = await permission_repo.get(perm_id)
        if not perm:
            continue

        existing = await role_permission_repo.exists(role_id, perm_id)
        if not existing:
            rp = role_permission_repo.model(role_id=role_id, permission_id=perm_id)
            db.add(rp)

    await db.commit()
    await permission_cache.delete_all()
    return {"message": "Permissions assigned"}


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    user_repo: UserRepository = Depends(get_user_repo),
    _: User = AdminUser,
):
    users = await user_repo.get_multi_with_roles(skip=skip, limit=limit)
    return [UserResponse.from_orm_with_roles(u) for u in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db_session),
    user_repo: UserRepository = Depends(get_user_repo),
    _: User = AdminUser,
):
    user = await user_repo.get(user_id)
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
    user_repo: UserRepository = Depends(get_user_repo),
    user_role_repo: UserRoleRepository = Depends(get_user_role_repo),
    _: User = SuperAdminUser,
):
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await user_role_repo.assign_roles(user_id, role_update.role_ids)

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
    user_repo: UserRepository = Depends(get_user_repo),
    resource_acl_repo: ResourceACLRepository = Depends(get_resource_acl_repo),
    _: User = AdminUser,
):
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await resource_acl_repo.upsert_or_update(user_id, resource, resource_id, access)

    await db.commit()
    return {"message": "Resource ACL created/updated"}


@router.delete("/resource-acl/{acl_id}")
async def delete_resource_acl(
    acl_id: int,
    db: AsyncSession = Depends(get_db_session),
    resource_acl_repo: ResourceACLRepository = Depends(get_resource_acl_repo),
    _: User = AdminUser,
):
    acl = await resource_acl_repo.get(acl_id)
    if not acl:
        raise HTTPException(status_code=404, detail="ACL not found")

    await resource_acl_repo.remove(acl_id)
    await db.commit()
    return {"message": "ACL deleted"}
