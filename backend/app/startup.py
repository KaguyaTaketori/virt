# backend/app/startup.py
"""
应用启动/关闭生命周期的各项初始化职责。
每个函数单一职责，可独立测试，可独立禁用。
"""

from __future__ import annotations
from typing import Optional

from redis import Redis
from sqlalchemy import select, func

from app.loguru_config import logger
from app.config import settings
from app.worker.scheduler import scheduler_service
from app.models.models import WebSubSubscription
from app.database import AsyncSessionFactory, create_all_tables, engine, Base
from app.services.redis_client import RedisClient
from app.services.token_blacklist import token_blacklist
from app.services.bilibili_auth import bilibili_auth_service
from app.integrations.websub.subscription_service import websub_service
from app.deps import init_deps
from app.integrations.api_client import BaseAPIClient
from app.integrations.bili_client import get_bili_client
from app.integrations.platform_registry import register_platform
from app.integrations.youtube import get_youtube_sync_service
from app.services.api_key_manager import api_key_manager
from app.worker.tasks import (
    update_bilibili_streams,
    update_youtube_streams,
    discover_live_streams_from_videos,
    daily_backfill_sync,
)


async def check_production_secrets() -> None:
    """生产环境安全断言，非生产环境直接返回。"""
    if settings.env.lower() != "prod":
        return

    errors = []
    if not settings.jwt_secret_key or len(settings.jwt_secret_key) < 32:
        errors.append("JWT_SECRET_KEY 未设置或长度不足（生产环境必须 ≥32 字符）")
    if not settings.websub_secret:
        errors.append("WEBSUB_SECRET 未设置")
    if not settings.youtube_api_keys_list:
        logger.warning("YOUTUBE_API_KEY 未设置，YouTube 功能不可用")
    if not settings.cors_origins:
        errors.append("CORS_ORIGINS 未设置")

    if errors:
        for e in errors:
            logger.critical("启动安全检查失败: {}", e)
        raise RuntimeError(
            "生产环境安全检查未通过：\n" + "\n".join(f"  - {e}" for e in errors)
        )


async def init_databases() -> None:
    """建表（幂等），使用异步引擎。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await create_all_tables()
    logger.info("Database tables verified/created")


async def init_api_keys() -> None:
    """初始化 API keys"""
    api_key_manager.initialize(settings.youtube_api_keys_list)
    logger.info("API keys initialized")


async def init_redis() -> Optional[Redis]:
    try:
        redis = await RedisClient.get_client()
        await redis.ping()
        logger.info("Redis connected")
        return redis
    except Exception as e:
        logger.warning(
            "Redis unavailable ({}), running in degraded mode: "
            "token blacklist, permission cache and danmaku queue disabled",
            e,
        )
        return None


async def init_token_blacklist(redis: Optional[Redis]) -> None:
    if redis is None:
        logger.warning("Token blacklist disabled: no Redis")
        return
    await token_blacklist.init(redis)
    await token_blacklist.warm_up()
    logger.info("Token blacklist warmed up")


async def init_websub() -> None:
    """首次启动时订阅 WebSub（仅在未配置或首次运行时执行）。"""
    callback_url = settings.websub_callback_url
    if not callback_url or callback_url == "https://your-domain.com/api/websub/youtube":
        logger.info("WebSub callback URL not configured, skipping initial subscription")
        return

    async with AsyncSessionFactory() as session:
        result = await session.execute(select(func.count(WebSubSubscription.id)))
        has_subscriptions = result.scalar() > 0

    if not has_subscriptions:
        try:
            await websub_service.subscribe_all_active(callback_url)
        except Exception as e:
            logger.error("首次 WebSub 订阅失败（不影响启动）: {}", e)


async def register_scheduled_jobs() -> None:
    """注册所有定时任务，启动调度器（使用 RedisJobStore）。"""
    bilibili_auth_service.start_cleanup_task()

    await scheduler_service.start()

    scheduler_service.add_interval_job(
        update_bilibili_streams, "update_bilibili_streams", seconds=60
    )
    scheduler_service.add_interval_job(
        update_youtube_streams, "update_youtube_streams", seconds=300
    )
    scheduler_service.add_interval_job(
        discover_live_streams_from_videos, "discover_live_streams", seconds=3600
    )
    scheduler_service.add_interval_job(
        daily_backfill_sync, "daily_backfill_sync", seconds=3600
    )

    logger.info("Scheduler started with all jobs registered")


async def cleanup_resources() -> None:
    """应用关闭时清理资源"""
    await scheduler_service.shutdown()
    await BaseAPIClient.close_client()
    logger.info("Resources cleaned up")


def register_platforms() -> None:
    register_platform(get_youtube_sync_service())
    register_platform(get_bili_client())
