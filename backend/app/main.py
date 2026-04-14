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
from app.routers.youtube_websub import router as youtube_websub_router
from app.startup import (
    check_production_secrets,
    init_databases,
    init_redis,
    init_token_blacklist,
    init_websub,
    init_api_keys,
    register_platforms,
    register_scheduled_jobs,
    cleanup_resources,
)
from app.services.danmaku_queue import init_danmaku_queue
from app.services.permission_cache import init_permission_cache
from app.services.quota_guard import init_quota_guard
from app.services.room_counter import init_room_counter


@asynccontextmanager
async def lifespan(app):
    await check_production_secrets()
    await init_databases()

    redis = await init_redis()

    await init_token_blacklist(redis)
    await init_permission_cache(redis)
    await init_danmaku_queue(redis)
    await init_room_counter(redis)

    if redis:
        await init_quota_guard(redis)
    await init_websub()
    await init_api_keys()
    await register_scheduled_jobs()
    register_platforms()
    logger.info("Application startup complete")
    yield
    await cleanup_resources()


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
        "Request: {} {} | Status: {} | Time: {:.2f}ms | Ip: {}",
        request.method,
        request.url.path,
        response.status_code,
        process_time,
        request.client.host if request.client else "unknown",
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
