from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.deps import get_db
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
from app.services.permissions import get_user_roles

router = APIRouter(prefix="/api/admin/permissions", tags=["permissions"])


def require_superadmin(db: Session, current_user: User):
    roles = get_user_roles(current_user.id, db)
    if "superadmin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin permission required",
        )


def require_admin(db: Session, current_user: User):
    roles = get_user_roles(current_user.id, db)
    if "superadmin" not in roles and "admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required"
        )


@router.get("/users/me", response_model=UserResponse)
def get_current_user_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前登录用户的信息"""
    resp = UserResponse.model_validate(current_user)
    resp.roles = get_user_roles(current_user.id, db)
    return resp


@router.get("/roles", response_model=List[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_superadmin(db, current_user)
    return db.query(Role).all()


@router.post("/roles", response_model=RoleResponse)
def create_role(
    role: RoleResponse,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_superadmin(db, current_user)

    existing = db.query(Role).filter(Role.name == role.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Role already exists")

    db_role = Role(name=role.name, description=role.description)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role


@router.get("/permissions", response_model=List[PermissionResponse])
def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(db, current_user)
    return db.query(Permission).all()


@router.post("/permissions", response_model=PermissionResponse)
def create_permission(
    permission: PermissionResponse,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_superadmin(db, current_user)

    existing = db.query(Permission).filter(Permission.name == permission.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Permission already exists")

    db_perm = Permission(
        name=permission.name,
        description=permission.description,
        resource=permission.resource,
        action=permission.action,
    )
    db.add(db_perm)
    db.commit()
    db.refresh(db_perm)
    return db_perm


@router.post("/roles/{role_id}/permissions")
def assign_permissions_to_role(
    role_id: int,
    permission_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_superadmin(db, current_user)

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    for perm_id in permission_ids:
        perm = db.query(Permission).filter(Permission.id == perm_id).first()
        if not perm:
            continue

        existing = (
            db.query(RolePermission)
            .filter(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == perm_id,
            )
            .first()
        )

        if not existing:
            rp = RolePermission(role_id=role_id, permission_id=perm_id)
            db.add(rp)

    db.commit()
    return {"message": "Permissions assigned"}


@router.get("/users", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(db, current_user)

    users = db.query(User).offset(skip).limit(limit).all()
    result = []
    for user in users:
        resp = UserResponse.model_validate(user)
        resp.roles = get_user_roles(user.id, db)
        result.append(resp)
    return result


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(db, current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    resp = UserResponse.model_validate(user)
    resp.roles = get_user_roles(user.id, db)
    return resp


@router.put("/users/{user_id}/roles")
def update_user_roles(
    user_id: int,
    role_update: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_superadmin(db, current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.query(UserRole).filter(UserRole.user_id == user_id).delete()

    for role_id in role_update.role_ids:
        role = db.query(Role).filter(Role.id == role_id).first()
        if role:
            ur = UserRole(user_id=user_id, role_id=role_id)
            db.add(ur)

    db.commit()
    return {"message": "Roles updated"}


@router.post("/users/{user_id}/resource-acl")
def create_resource_acl(
    user_id: int,
    resource: str,
    resource_id: int,
    access: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(db, current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = (
        db.query(ResourceACL)
        .filter(
            ResourceACL.user_id == user_id,
            ResourceACL.resource == resource,
            ResourceACL.resource_id == resource_id,
        )
        .first()
    )

    if existing:
        existing.access = access
    else:
        acl = ResourceACL(
            user_id=user_id, resource=resource, resource_id=resource_id, access=access
        )
        db.add(acl)

    db.commit()
    return {"message": "Resource ACL created/updated"}


@router.delete("/resource-acl/{acl_id}")
def delete_resource_acl(
    acl_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(db, current_user)

    acl = db.query(ResourceACL).filter(ResourceACL.id == acl_id).first()
    if not acl:
        raise HTTPException(status_code=404, detail="ACL not found")

    db.delete(acl)
    db.commit()
    return {"message": "ACL deleted"}
