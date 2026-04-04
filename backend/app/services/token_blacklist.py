"""
backend/app/services/token_blacklist.py
─────────────────────────────────────────────────────────────────────────────
Token 黑名单服务（修复 [致命] JWT 无法撤销问题）

方案：使用内存 + SQLite 持久化的双层黑名单。
  - 内存层（set）：O(1) 查询，进程重启后从 DB 恢复。
  - DB 层（token_blacklist 表）：持久化，支持多进程/多实例场景。

生产环境升级路径：
  将 DB 层替换为 Redis（`redis.asyncio`），TTL 自动清理过期 token。
  详见文件底部的 RedisTokenBlacklist 类（注释状态）。
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from jose import jwt, JWTError
from sqlalchemy import Column, DateTime, Integer, String, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base
from app.config import settings
from app.loguru_config import logger


# ── 数据库模型 ─────────────────────────────────────────────────────────────────

class BlacklistedToken(Base):
    """记录已撤销的 JWT Token，按 jti（Token ID）索引。"""

    __tablename__ = "blacklisted_tokens"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, nullable=False)
    expired_at = Column(DateTime, nullable=False)   # Token 自然过期时间
    revoked_at = Column(DateTime, nullable=False)   # 手动撤销时间


# ── 黑名单服务 ─────────────────────────────────────────────────────────────────

class TokenBlacklistService:
    """
    双层 Token 黑名单：内存缓存 + SQLite 持久化。

    初始化：在 FastAPI lifespan 中调用 `await service.warm_up(db)`。
    """

    def __init__(self) -> None:
        self._cache: set[str] = set()   # 内存层（进程级缓存）
        self._lock = asyncio.Lock()

    async def warm_up(self, db: AsyncSession) -> None:
        """启动时从数据库加载未过期的黑名单 token 到内存缓存。"""
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(BlacklistedToken.jti).where(BlacklistedToken.expired_at > now)
        )
        jtis = result.scalars().all()
        async with self._lock:
            self._cache.update(jtis)
        logger.info("Token blacklist warmed up with {} entries", len(jtis))

    async def revoke(self, token: str, db: AsyncSession, user_id: int) -> None:
        """
        撤销一个 Token。
        调用方：logout 接口，或管理员强制踢人接口。
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": False},   # 允许处理已过期的 token
            )
        except JWTError as e:
            logger.warning("Cannot revoke invalid token: {}", e)
            return

        jti: Optional[str] = payload.get("jti")
        exp: Optional[int] = payload.get("exp")

        if not jti:
            # 旧格式 token（无 jti），按 sub+exp 生成伪 jti
            sub = payload.get("sub", "unknown")
            jti = f"{sub}:{exp}"

        expired_at = (
            datetime.fromtimestamp(exp, tz=timezone.utc)
            if exp
            else datetime.now(timezone.utc)
        )

        # 写入数据库
        record = BlacklistedToken(
            jti=jti,
            user_id=user_id,
            expired_at=expired_at,
            revoked_at=datetime.now(timezone.utc),
        )
        db.add(record)
        await db.commit()

        # 写入内存缓存
        async with self._lock:
            self._cache.add(jti)

        logger.info("Token revoked | user_id={} jti={}", user_id, jti)

    def is_blacklisted(self, jti: str) -> bool:
        """
        检查 jti 是否在黑名单中（仅查内存缓存，O(1) 性能）。
        在 get_current_user 中调用此方法。
        """
        return jti in self._cache

    async def cleanup_expired(self, db: AsyncSession) -> int:
        """
        清理已自然过期的黑名单记录（可注册为定时任务，每天执行一次）。
        返回清理数量。
        """
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(BlacklistedToken.jti).where(BlacklistedToken.expired_at <= now)
        )
        expired_jtis = set(result.scalars().all())

        await db.execute(
            delete(BlacklistedToken).where(BlacklistedToken.expired_at <= now)
        )
        await db.commit()

        async with self._lock:
            self._cache -= expired_jtis

        logger.info("Cleaned up {} expired blacklist entries", len(expired_jtis))
        return len(expired_jtis)


# 全局单例
token_blacklist = TokenBlacklistService()


# ─────────────────────────────────────────────────────────────────────────────
# 生产环境升级：Redis 实现（替换上方 SQLite 版本，使用 TTL 自动清理）
# ─────────────────────────────────────────────────────────────────────────────
# import redis.asyncio as aioredis
#
# class RedisTokenBlacklist:
#     def __init__(self, redis_url: str = "redis://localhost:6379/0"):
#         self._redis = aioredis.from_url(redis_url, decode_responses=True)
#
#     async def revoke(self, token: str, user_id: int) -> None:
#         payload = jwt.decode(token, settings.jwt_secret_key, ...)
#         jti = payload.get("jti") or f"{payload['sub']}:{payload['exp']}"
#         exp = payload.get("exp", 0)
#         ttl = max(0, exp - int(datetime.now(timezone.utc).timestamp()))
#         await self._redis.setex(f"bl:{jti}", ttl, "1")
#
#     async def is_blacklisted(self, jti: str) -> bool:
#         return bool(await self._redis.exists(f"bl:{jti}"))