from __future__ import annotations

import asyncio
from datetime import timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    get_current_user,
    get_db_session,
    get_password_hash,
    verify_password,
    get_token_jti_and_exp,
)
from app.config import settings
from app.models.models import User, UserLoginLog, UserRole, Role
from app.schemas.schemas import Token, UserCreate, UserResponse
from app.services.token_blacklist import token_blacklist
from app.services.permission_cache import permission_cache

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

_DUMMY_HASH = get_password_hash("__dummy_password_for_timing__")

_PRIVATE_PREFIXES = ("127.", "10.", "192.168.", "::1", "localhost")


# ── IP 工具 ───────────────────────────────────────────────────────────────────


def get_client_ip(request: Request) -> str:
    for header in ("CF-Connecting-IP", "X-Real-IP", "X-Forwarded-For"):
        val = request.headers.get(header)
        if val:
            return val.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_private_ip(ip: str) -> bool:
    return ip == "unknown" or any(ip.startswith(p) for p in _PRIVATE_PREFIXES)


def _fetch_ip_info_sync(ip: str) -> dict:
    empty = {"country": None, "region": None, "city": None, "isp": None}
    try:
        resp = httpx.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,country,regionName,city,isp"},
            timeout=5.0,
        )
        data = resp.json()
        if data.get("status") == "success":
            return {
                "country": data.get("country"),
                "region": data.get("regionName"),
                "city": data.get("city"),
                "isp": data.get("isp"),
            }
    except Exception:
        pass
    return empty


async def get_ip_info(ip: str) -> dict:
    if _is_private_ip(ip):
        return {"country": None, "region": None, "city": None, "isp": None}
    return await asyncio.to_thread(_fetch_ip_info_sync, ip)


async def record_login_log(
    db: AsyncSession,
    user_id: int,
    request: Request,
    success: bool,
    fail_reason: str = None,
) -> None:
    ip = get_client_ip(request)
    ip_info = await get_ip_info(ip)
    log = UserLoginLog(
        user_id=user_id,
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
        success=success,
        fail_reason=fail_reason,
        **ip_info,
    )
    db.add(log)
    await db.commit()


# ── 注册 ──────────────────────────────────────────────────────────────────────


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    user: UserCreate,
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(select(User).where(User.username == user.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please try a different username or email.",
        )

    if user.email:
        result = await db.execute(select(User).where(User.email == user.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed. Please try a different username or email.",
            )

    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    result = await db.execute(select(Role).where(Role.name == "user"))
    user_role = result.scalar_one_or_none()
    if user_role:
        db.add(UserRole(user_id=db_user.id, role_id=user_role.id))
        await db.commit()

    await record_login_log(db, db_user.id, request, True)
    return db_user


# ── 登录 ──────────────────────────────────────────────────────────────────────


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    password_to_check = user.hashed_password if user else _DUMMY_HASH
    password_valid = verify_password(form_data.password, password_to_check)

    if not user or not password_valid:
        if user:
            await record_login_log(db, user.id, request, False, "Incorrect password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await record_login_log(db, user.id, request, True)

    access_token, jti = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )

    from jose import jwt as jose_jwt

    payload = jose_jwt.decode(
        access_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    token_exp = payload.get("exp", 0)

    from app.services.permissions import get_user_roles, get_all_permissions_for_user

    roles = await get_user_roles(user.id, db)
    permissions = await get_all_permissions_for_user(user.id, db)
    await permission_cache.set_permissions(jti, roles, permissions, token_exp)

    return {"access_token": access_token, "token_type": "bearer"}


# ── 注销 ──────────────────────────────────────────────────────────────────────

_bearer_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    token: str = Depends(_bearer_scheme),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    if token:
        await token_blacklist.revoke(token, db, current_user.id)
        try:
            jti, _ = get_token_jti_and_exp(token)
            if jti:
                await permission_cache.delete_permissions(jti)
        except Exception:
            pass

    response.delete_cookie("access_token", path="/")
    return {"message": "Logged out successfully. Token has been revoked."}
