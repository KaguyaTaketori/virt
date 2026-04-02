from functools import wraps
from typing import Optional, Callable, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.deps import get_db
from app.models.models import (
    User,
    Role,
    Permission,
    UserRole,
    RolePermission,
    ResourceACL,
)
from app.auth import get_current_user_optional


oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login", auto_error=False
)


class AllowAnonymous:
    """标记该接口允许访客访问（无需认证）"""

    pass


def require_permission(resource: str, action: str):
    """装饰器：要求特定权限"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取db和current_user
            db = kwargs.get("db")
            current_user = kwargs.get("current_user")

            if not db or not current_user:
                from app.deps import get_db as original_get_db
                from app.auth import get_current_user_optional

                db = next(original_get_db())
                current_user = await get_current_user_optional(db=db)

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            checker = PermissionChecker(resource, action)
            if not checker._check_permission(db, current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {resource}.{action}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


class PermissionChecker:
    """权限检查器，支持角色和资源级权限检查"""

    def __init__(self, resource: str, action: str, resource_id: Optional[int] = None):
        self.resource = resource
        self.action = action
        self.resource_id = resource_id

    def __call__(
        self,
        current_user: Optional[User] = Depends(get_current_user_optional),
        db: Session = Depends(get_db),
    ) -> User:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        if not self._check_permission(db, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {self.resource}.{self.action}",
            )

        return current_user

    def _check_permission(self, db: Session, user_id: int) -> bool:
        # 1. 检查角色权限
        user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
        role_ids = [ur.role_id for ur in user_roles]

        if not role_ids:
            return False

        # 2. 检查是否有对应的权限
        perms = (
            db.query(RolePermission)
            .filter(
                RolePermission.role_id.in_(role_ids),
                RolePermission.permission.has(
                    Permission.resource == self.resource,
                    Permission.action == self.action,
                ),
            )
            .first()
        )

        if perms:
            return True

        # 3. 检查资源级ACL
        if self.resource_id:
            acl = (
                db.query(ResourceACL)
                .filter(
                    ResourceACL.user_id == user_id,
                    ResourceACL.resource == self.resource,
                    ResourceACL.resource_id == self.resource_id,
                    ResourceACL.access.in_(["owner", "editor"]),
                )
                .first()
            )
            if acl:
                return True

        return False


def require_permission(resource: str, action: str):
    """装饰器：要求特定权限"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取db和current_user
            db = kwargs.get("db")
            current_user = kwargs.get("current_user")

            if not db or not current_user:
                from app.deps import get_db as original_get_db
                from app.auth import get_current_user_optional

                db = next(original_get_db())
                current_user = await get_current_user_optional(db=db)

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            checker = PermissionChecker(resource, action)
            if not checker._check_permission(db, current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {resource}.{action}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


async def get_current_user_with_roles(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """获取当前用户并加载角色信息"""
    if not token:
        return None

    from jose import JWTError, jwt
    from app.config import settings

    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            return None

        user = db.query(User).filter(User.username == username).first()
        if user:
            user_roles = db.query(UserRole).filter(UserRole.user_id == user.id).all()
            user._roles = [
                db.query(Role).filter(Role.id == ur.role_id).first()
                for ur in user_roles
            ]
        return user
    except JWTError:
        return None


class OwnershipVerifier:
    """所有权校验器，防止水平越权"""

    @staticmethod
    def verify_ownership(
        user_id: int,
        resource: str,
        resource_id: int,
        db: Session,
        require_owner: bool = True,
    ) -> bool:
        """
        验证用户是否拥有对资源的访问权限
        返回 True 表示有权限，False 表示无权限
        """
        # 1. 检查是否是资源的创建者/拥有者
        if resource == "channel":
            from app.models.models import Channel, UserChannel

            channel = db.query(Channel).filter(Channel.id == resource_id).first()
            if channel:
                # 检查是否是通过UserChannel创建的
                uc = (
                    db.query(UserChannel)
                    .filter(
                        UserChannel.user_id == user_id,
                        UserChannel.channel_id == resource_id,
                    )
                    .first()
                )
                if uc:
                    return True

        # 2. 检查资源级ACL
        acl = (
            db.query(ResourceACL)
            .filter(
                ResourceACL.user_id == user_id,
                ResourceACL.resource == resource,
                ResourceACL.resource_id == resource_id,
            )
            .first()
        )

        if acl:
            if require_owner and acl.access == "viewer":
                return False
            return True

        # 3. 检查用户角色是否有该资源的管理权限
        user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
        role_ids = [ur.role_id for ur in user_roles]

        if role_ids:
            # 超级管理员始终有权限
            roles = (
                db.query(Role)
                .filter(Role.id.in_(role_ids), Role.name == "superadmin")
                .first()
            )
            if roles:
                return True

            # 管理员有全部权限
            roles = (
                db.query(Role)
                .filter(Role.id.in_(role_ids), Role.name == "admin")
                .first()
            )
            if roles:
                return True

        return False

    @staticmethod
    def require_ownership(
        user_id: int,
        resource: str,
        resource_id: int,
        db: Session,
        require_owner: bool = True,
    ):
        """验证失败时抛出异常"""
        if not OwnershipVerifier.verify_ownership(
            user_id, resource, resource_id, db, require_owner
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to {resource}:{resource_id}",
            )


def get_user_roles(user_id: int, db: Session) -> list[str]:
    """获取用户所有角色名称"""
    user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    role_ids = [ur.role_id for ur in user_roles]
    if not role_ids:
        return []

    roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
    return [r.name for r in roles]


def has_role(user_id: int, role_name: str, db: Session) -> bool:
    """检查用户是否有特定角色"""
    user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    role_ids = [ur.role_id for ur in user_roles]
    if not role_ids:
        return False

    return (
        db.query(Role).filter(Role.id.in_(role_ids), Role.name == role_name).first()
        is not None
    )


def has_permission(user_id: int, resource: str, action: str, db: Session) -> bool:
    """检查用户是否有特定权限（基于角色）"""
    user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    role_ids = [ur.role_id for ur in user_roles]
    if not role_ids:
        return False

    return (
        db.query(RolePermission)
        .join(Permission)
        .filter(
            RolePermission.role_id.in_(role_ids),
            Permission.resource == resource,
            Permission.action == action,
        )
        .first()
        is not None
    )


def assign_role(user_id: int, role_id: int, db: Session):
    """为用户分配角色"""
    existing = (
        db.query(UserRole)
        .filter(UserRole.user_id == user_id, UserRole.role_id == role_id)
        .first()
    )

    if existing:
        return

    user_role = UserRole(user_id=user_id, role_id=role_id)
    db.add(user_role)
    db.commit()


def remove_role(user_id: int, role_id: int, db: Session):
    """移除用户角色"""
    db.query(UserRole).filter(
        UserRole.user_id == user_id, UserRole.role_id == role_id
    ).delete()
    db.commit()
