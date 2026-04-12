"""
backend/app/services/token_blacklist.py
────────────────────────────────────────────────────────────────────────────
Token 黑名单服务 - 基于 Redis 实现，TTL 自动清理过期 token。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from jose import jwt, JWTError
from redis.asyncio import Redis

from app.config import settings
from app.loguru_config import logger


# ── 黑名单服务 ─────────────────────────────────────────────────────────────────


class TokenBlacklist:
    def __init__(self) -> None:
        self._redis: Optional[Redis] = None
        self._local_cache: set[str] = set()
        self._lock = asyncio.Lock()

    async def init(self, redis: Redis) -> None:
        """初始化，注入 redis 实例"""
        self._redis = redis

    def _key(self, jti: str) -> str:
        return f"blacklist:jti:{jti}"

    async def warm_up(self) -> None:
        """启动预热：从 Redis 加载当前黑名单到 L1 缓存"""
        if self._redis is None:
            logger.warning("TokenBlacklist not initialized, skipping warm_up")
            return

        cursor = 0
        count = 0
        while True:
            cursor, keys = await self._redis.scan(
                cursor, match="blacklist:jti:*", count=200
            )
            for key in keys:
                jti = key.removeprefix("blacklist:jti:")
                self._local_cache.add(jti)
                count += 1
            if cursor == 0:
                break
        logger.info("Token blacklist warmed up with {} entries from Redis", count)

    async def revoke(self, token: str, user_id: int) -> None:
        if self._redis is None:
            logger.warning("TokenBlacklist not initialized")
            return

        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": False},
            )
        except JWTError as e:
            logger.warning("Cannot revoke invalid token: {}", e)
            return

        jti: str = payload.get("jti", "")
        exp: int = payload.get("exp", 0)
        if not jti:
            return

        ttl = max(exp - int(datetime.now(timezone.utc).timestamp()), 60)

        await self._redis.setex(self._key(jti), ttl, "1")
        async with self._lock:
            self._local_cache.add(jti)

        logger.info("Token revoked | user_id={} jti={} ttl={}s", user_id, jti, ttl)

    def is_blacklisted(self, jti: str) -> bool:
        """检查 jti 是否在黑名单中（仅查内存缓存，O(1) 性能）"""
        return jti in self._local_cache


# 全局单例
token_blacklist = TokenBlacklist()
