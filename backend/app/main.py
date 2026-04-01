import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routers import (
    streams,
    channels,
    danmaku,
    admin,
    websocket,
    organizations,
    auth,
    user_channels,
)
from app.services.youtube_websub import router as youtube_websub_router
from app.database import engine, Base
from app.scheduler_tasks import start_scheduler
from app.config import settings

log = logging.getLogger(__name__)


async def _initial_websub_subscription():
    """首次启动时自动订阅所有活跃的 YouTube 频道"""
    callback_url = settings.websub_callback_url
    if not callback_url or callback_url == "https://your-domain.com/api/websub/youtube":
        log.info("未配置回调 URL，跳过首次订阅")
        return

    from app.database_async import AsyncSessionFactory
    from sqlalchemy import select, func
    from app.models.models import WebSubSubscription

    async with AsyncSessionFactory() as session:
        result = await session.execute(select(func.count(WebSubSubscription.id)))
        has_subscriptions = result.scalar() > 0

    if has_subscriptions:
        log.info("已有订阅记录，跳过首次订阅")
        return

    from app.services.youtube_websub import subscribe_all_active_channels

    log.info("首次启动，开始自动订阅...")
    try:
        await subscribe_all_active_channels(callback_url)
    except Exception as e:
        log.error(f"首次订阅失败: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    await _initial_websub_subscription()
    yield


app = FastAPI(
    title="VTuber Live Aggregator API",
    description="聚合 YouTube 和 Bilibili 直播流的后端 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(streams.router)
app.include_router(channels.router)
app.include_router(danmaku.router)
app.include_router(admin.router)
app.include_router(websocket.router)
app.include_router(organizations.router)
app.include_router(auth.router)
app.include_router(user_channels.router)
app.include_router(youtube_websub_router)


@app.get("/")
def root():
    return {"message": "VTuber Live Aggregator API", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
