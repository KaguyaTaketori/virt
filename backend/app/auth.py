"""
backend/app/auth.py  ← 完整替换原文件
─────────────────────────────────────────────────────────────────────────────
修复内容：
  [致命] 注销后 Token 依然有效
    → create_access_token 加入 jti 字段
    → get_current_user 校验 Token 是否在黑名单中
  [高]   用户枚举漏洞（注册接口区分"用户名已存在"/"邮箱已存在"）
    → 统一错误信息（详见 auth 路由文件）
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import hashlib
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.deps.base import get_async_db
from app.config import settings
from app.models.models import User
from app.schemas.schemas import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ── 密码工具 ───────────────────────────────────────────────────────────────────

def _pre_hash_password(password: str) -> str:
    """SHA-256 预哈希，避免 bcrypt 72 字节截断限制。"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pre_hashed = _pre_hash_password(plain_password)
    return bcrypt.checkpw(pre_hashed.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    pre_hashed = _pre_hash_password(password)
    return bcrypt.hashpw(pre_hashed.encode("utf-8"), bcrypt.gensalt()).decode()


# ── Token 创建（新增 jti 字段）────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT，每个 Token 携带唯一 jti（Token ID），用于精确撤销。
    jti 使用 UUID4，概率碰撞极低（2^122 分之一）。
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode.update({
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "iat": datetime.now(timezone.utc),
    })
    return jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


# ── Token 解析与验证（增加黑名单检查）────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """
    验证 Token 并返回当前用户。
    新增检查：Token 是否在黑名单中（已注销/被管理员踢出）。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        username: str = payload.get("sub")
        jti: str = payload.get("jti", "")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    # ── 黑名单检查（O(1) 内存查询）──────────────────────────────────────────
    from app.services.token_blacklist import token_blacklist
    if jti and token_blacklist.is_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.username == token_data.username))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_optional(
    token: str = Depends(
        OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
    ),
    db: AsyncSession = Depends(get_async_db),
) -> Optional[User]:
    """可选认证：无 Token 时返回 None 而非抛异常。"""
    if not token:
        return None
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        username: str = payload.get("sub")
        jti: str = payload.get("jti", "")
        if username is None:
            return None

        # 黑名单检查
        from app.services.token_blacklist import token_blacklist
        if jti and token_blacklist.is_blacklisted(jti):
            return None

        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
    except JWTError:
        return None