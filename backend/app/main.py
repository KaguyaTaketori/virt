from app.loguru_config import logger
from app.config import settings
import time
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy import text, select, func

from app.routers import (
    streams,
    channels,
    danmaku,
    admin,
    websocket,
    organizations,
    auth,
    user_channels,
    permissions,
    bilibili_auth,
)
from app.services.token_blacklist import token_blacklist
from app.services.youtube_websub import (
    router as youtube_websub_router,
    subscribe_all_active_channels,
)
from app.schedulers import start_scheduler, scheduler
from app.database_async import AsyncSessionFactory, create_all_tables
from app.database import engine, Base
from app.models.models import WebSubSubscription
from app.services.redis_client import RedisClient
from app.services.permission_cache import init_permission_cache
from app.services.room_counter import init_room_counter
from app.services.danmaku_queue import init_danmaku_queue
from app.startup import (
    check_production_secrets,
    init_databases,
    init_redis,
    init_token_blacklist,
    init_websub,
    register_scheduled_jobs,
)

def _assert_production_secrets() -> None:
    env = settings.env.lower()
    if env != "prod":
        return

    errors = []

    if not settings.jwt_secret_key or len(settings.jwt_secret_key) < 32:
        errors.append("JWT_SECRET_KEY 未设置或长度不足（生产环境必须 ≥32 字符）")

    if not settings.websub_secret:
        errors.append("WEBSUB_SECRET 未设置（生产环境必须配置）")

    if not settings.youtube_api_keys_list:
        logger.warning("YOUTUBE_API_KEY 未设置，YouTube 功能不可用")

    if not settings.cors_origins:
        errors.append("CORS_ORIGINS 未设置（生产环境必须显式指定允许的前端域名）")

    if errors:
        for e in errors:
            logger.critical("启动安全检查失败: {}", e)
        raise RuntimeError(
            "生产环境安全检查未通过：\n" + "\n".join(f"  - {e}" for e in errors)
        )


@asynccontextmanager
async def lifespan(app):
    """
    应用生命周期编排器。
    职责：按顺序调用各初始化模块，处理整体启动失败。
    """
    try:
        await check_production_secrets()   # 1. 安全断言
        await init_databases()             # 2. 建表
        await init_redis()                 # 3. Redis（失败可降级）
        await init_token_blacklist()       # 4. 黑名单预热
        await init_websub()               # 5. WebSub 订阅
        await register_scheduled_jobs()   # 6. 定时任务
        logger.info("Application startup complete")
    except Exception as e:
        logger.critical("Application startup failed: {}", e)
        raise

    yield

    logger.info("Application shutting down...")

limiter = Limiter(key_func=get_remote_address)


def create_app() -> FastAPI:
    app = FastAPI(
        title="VTuber Live Aggregator API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=settings.cors_allowed_methods_list,
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
        expose_headers=["X-Total-Count"],
    )

    return app


app = create_app()

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "未处理异常 | {} {} | {}",
        request.method,
        request.url.path,
        exc,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "服务器内部错误，请稍后重试"},
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000

    logger.bind(access=True).info(
        "Request: {} {} | Status: {} | Time: {:.2f}ms",
        request.method,
        request.url.path,
        response.status_code,
        process_time,
    )
    return response


app.include_router(streams.router)
app.include_router(channels.router)
app.include_router(danmaku.router)
app.include_router(admin.router)
app.include_router(websocket.router)
app.include_router(organizations.router)
app.include_router(auth.router)
app.include_router(user_channels.router)
app.include_router(permissions.router)
app.include_router(youtube_websub_router)
app.include_router(bilibili_auth.router)


@app.get("/")
def root():
    return {"message": "VTuber Live Aggregator API", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
