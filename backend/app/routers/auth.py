import asyncio
from datetime import timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_db, get_password_hash, verify_password
from app.config import settings
from app.models.models import User, UserLoginLog
from app.schemas.schemas import Token, UserCreate, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

_PRIVATE_PREFIXES = ("127.", "10.", "192.168.", "::1", "localhost")
_DUMMY_HASH = get_password_hash("__dummy_password_for_timing__")

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
    """纯同步函数，由 asyncio.to_thread 在线程池中执行，不阻塞事件循环"""
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
    """异步包装：私有 IP 直接返回，公网 IP 卸载到线程池"""
    if _is_private_ip(ip):
        return {"country": None, "region": None, "city": None, "isp": None}
    return await asyncio.to_thread(_fetch_ip_info_sync, ip)

async def record_login_log(
    db: Session, user_id: int, request: Request,
    success: bool, fail_reason: str = None,
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
    db.commit()


# ── 路由 ──────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    user: UserCreate,
    db: Session = Depends(get_db),
):
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
 
    if user.email:
        existing_email = db.query(User).filter(User.email == user.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
 
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
 
    record_login_log(db, db_user.id, request, True)
    return db_user


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == form_data.username).first()
 
    password_to_check = user.hashed_password if user else _DUMMY_HASH
    password_valid = verify_password(form_data.password, password_to_check)
    # ─────────────────────────────────────────────────────────────────────────
 
    if not user or not password_valid:
        if user:
            record_login_log(db, user.id, request, False, "Incorrect password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
 
    record_login_log(db, user.id, request, True)
 
    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}