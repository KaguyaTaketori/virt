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
async def lifespan(app: FastAPI):
    try:
        _assert_production_secrets()

        Base.metadata.create_all(bind=engine)
        await create_all_tables()

        try:
            redis = await RedisClient.get_client()
            await redis.ping()
            await init_permission_cache(redis)
            await init_room_counter(redis)
            await init_danmaku_queue(redis)
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning("Redis connection failed, permission cache disabled: {}", e)

        try:
            async with AsyncSessionFactory() as session:
                await session.execute(
                    text("""
                    CREATE TABLE IF NOT EXISTS blacklisted_tokens (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        jti VARCHAR(64) UNIQUE NOT NULL,
                        user_id INTEGER NOT NULL,
                        expired_at DATETIME NOT NULL,
                        revoked_at DATETIME NOT NULL
                    )
                """)
                )
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_blacklisted_tokens_jti ON blacklisted_tokens (jti)"
                    )
                )
                await session.commit()
                await token_blacklist.warm_up(session)
        except Exception as e:
            logger.error("Token blacklist warmup failed: {}", e)

        callback_url = settings.websub_callback_url
        if (
            not callback_url
            or callback_url == "https://your-domain.com/api/websub/youtube"
        ):
            logger.info("未配置回调 URL，跳过首次订阅")
        else:
            async with AsyncSessionFactory() as session:
                result = await session.execute(
                    select(func.count(WebSubSubscription.id))
                )
                has_subscriptions = result.scalar() > 0
            if not has_subscriptions:
                try:
                    await subscribe_all_active_channels(callback_url)
                except Exception as e:
                    logger.error("首次订阅失败: {}", e)

        start_scheduler()

        async def _cleanup_blacklist():
            try:
                async with AsyncSessionFactory() as session:
                    count = await token_blacklist.cleanup_expired(session)
                    if count:
                        logger.info("Cleaned {} expired blacklist entries", count)
            except Exception as e:
                logger.error("Blacklist cleanup error: {}", e)

        scheduler.add_job(
            _cleanup_blacklist,
            "cron",
            hour=3,
            minute=30,
            id="blacklist_cleanup",
            replace_existing=True,
        )

        yield
        logger.info("Application shutting down...")
    except Exception as e:
        logger.critical("Application startup failed: {}", e)
        logger.exception(e)
        raise e


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


@app.get("/")
def root():
    return {"message": "VTuber Live Aggregator API", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
