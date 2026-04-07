# backend/app/startup.py  ← 新建文件
"""
应用启动/关闭生命周期的各项初始化职责。
每个函数单一职责，可独立测试，可独立禁用。
"""
from __future__ import annotations

from sqlalchemy import text, select, func

from app.loguru_config import logger
from app.config import settings
from app.schedulers import start_scheduler, scheduler
from app.models.models import WebSubSubscription
from app.database_async import AsyncSessionFactory, create_all_tables
from app.database import engine, Base
from app.services.redis_client import RedisClient
from app.services.permission_cache import init_permission_cache
from app.services.room_counter import init_room_counter
from app.services.danmaku_queue import init_danmaku_queue
from app.services.token_blacklist import token_blacklist
from app.services.bilibili_auth import bilibili_auth_service
from app.services.youtube_websub import subscribe_all_active_channels


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
        raise RuntimeError("生产环境安全检查未通过：\n" + "\n".join(f"  - {e}" for e in errors))


async def init_databases() -> None:
    """建表（幂等），同步引擎 + 异步引擎均初始化。"""


    Base.metadata.create_all(bind=engine)
    await create_all_tables()
    logger.info("Database tables verified/created")


async def init_redis() -> bool:
    """
    初始化 Redis 及依赖它的子系统。
    返回 True 表示成功，False 表示降级运行（无 Redis）。
    """
    try:
        redis = await RedisClient.get_client()
        await redis.ping()
        await init_permission_cache(redis)
        await init_room_counter(redis)
        await init_danmaku_queue(redis)
        logger.info("Redis connected and subsystems initialized")
        return True
    except Exception as e:
        logger.warning("Redis unavailable, running in degraded mode: {}", e)
        return False


async def init_token_blacklist() -> None:
    """预热 Token 黑名单（SQLite 持久化 + 内存缓存）。"""
    async with AsyncSessionFactory() as session:
        # 确保表存在（idempotent DDL）
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS blacklisted_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jti VARCHAR(64) UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                expired_at DATETIME NOT NULL,
                revoked_at DATETIME NOT NULL
            )
        """))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_blacklisted_tokens_jti "
            "ON blacklisted_tokens (jti)"
        ))
        await session.commit()
        await token_blacklist.warm_up(session)

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
            await subscribe_all_active_channels(callback_url)
        except Exception as e:
            logger.error("首次 WebSub 订阅失败（不影响启动）: {}", e)


async def register_scheduled_jobs() -> None:
    """注册所有定时任务，与调度器启动解耦。"""
    bilibili_auth_service.start_cleanup_task()
    async def _cleanup_blacklist():
        try:
            async with AsyncSessionFactory() as session:
                count = await token_blacklist.cleanup_expired(session)
                if count:
                    logger.info("Cleaned {} expired blacklist entries", count)
        except Exception as e:
            logger.error("Blacklist cleanup error: {}", e)

    start_scheduler()
    scheduler.add_job(
        _cleanup_blacklist,
        "cron", hour=3, minute=30,
        id="blacklist_cleanup", replace_existing=True,
    )
    logger.info("Scheduler started with all jobs registered")