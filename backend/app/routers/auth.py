from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import User, UserLoginLog
from app.schemas.schemas import UserCreate, UserResponse, Token
from app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_db,
)
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_client_ip(request: Request) -> str:
    """从请求中获取真实IP，支持Cloudflare等代理"""
    # Cloudflare
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip

    # 常见的代理头
    for header in ["X-Real-IP", "X-Forwarded-For"]:
        ip = request.headers.get(header)
        if ip:
            return ip.split(",")[0].strip()

    # 直接连接
    if request.client:
        return request.client.host
    return "unknown"


def get_ip_info(ip: str) -> dict:
    """获取IP的地理信息"""
    if (
        ip == "unknown"
        or ip.startswith("127.")
        or ip.startswith("10.")
        or ip.startswith("192.168")
    ):
        return {"country": None, "region": None, "city": None, "isp": None}

    try:
        import httpx

        # 免费IP库，有请求限制 (45 requests/minute)
        response = httpx.get(
            f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp",
            timeout=5,
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return {
                    "country": data.get("country"),
                    "region": data.get("regionName"),
                    "city": data.get("city"),
                    "isp": data.get("isp"),
                }
    except Exception:
        pass

    return {"country": None, "region": None, "city": None, "isp": None}

    # 这里可以使用免费IP库，如 ip-api.com (有请求限制)
    # 生产环境建议使用本地IP库或付费服务
    return {"country": None, "region": None, "city": None, "isp": None}


def record_login_log(
    db: Session, user_id: int, request: Request, success: bool, fail_reason: str = None
):
    """记录登录日志"""
    ip = get_client_ip(request)
    ip_info = get_ip_info(ip)

    log = UserLoginLog(
        user_id=user_id,
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
        country=ip_info.get("country"),
        region=ip_info.get("region"),
        city=ip_info.get("city"),
        isp=ip_info.get("isp"),
        success=success,
        fail_reason=fail_reason,
    )
    db.add(log)
    db.commit()


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(user: UserCreate, request: Request, db: Session = Depends(get_db)):
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

    # 记录注册成功日志
    record_login_log(db, db_user.id, request, True)
    return db_user


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        # 记录登录失败
        if user:
            record_login_log(db, user.id, request, False, "Incorrect password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 记录登录成功
    record_login_log(db, user.id, request, True)

    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
