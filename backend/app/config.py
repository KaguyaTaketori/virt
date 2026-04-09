from __future__ import annotations

import secrets
from typing import Optional

from pydantic_settings import BaseSettings

_DEV_FALLBACK_JWT_SECRET = "dev-only-secret-do-not-use-in-production-vtuber-live-2024"


class Settings(BaseSettings):
    youtube_api_keys: str = ""
    bilibili_sessdata: str = ""
    db_url: str = "sqlite:///./streams.db"
    enable_danmaku: bool = False
    danmaku_storage_path: str = "./danmaku_data"
    websub_callback_url: str = ""
    websub_secret: str = ""

    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7

    superadmin_username: str = "admin"
    superadmin_password: str = ""

    cors_origins: Optional[str] = None
    cors_allowed_methods: str = "GET,POST,PUT,DELETE,OPTIONS"

    youtube_quota_daily_limit: int = 9_500
    youtube_quota_discover_reserve: int = 2_000

    env: str = "DEV"
    base_log_dir: str = "logs"

    redis_url: str = "redis://localhost:6379/0"

    max_ws_connections_per_video: int = 1000
    max_ws_connections_total: int = 10000

    @property
    def db_dialect(self) -> str:
        """从 db_url 推断数据库类型，整个应用共用同一判断逻辑。"""
        url = self.db_url.lower()
        if "postgresql" in url or "postgres" in url:
            return "postgresql"
        return "sqlite"  # 默认

    @property
    def is_sqlite(self) -> bool:
        return self.db_dialect == "sqlite"

    @property
    def is_postgresql(self) -> bool:
        return self.db_dialect == "postgresql"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def __init__(self, **data):
        super().__init__(**data)
        self._resolve_jwt_secret()

    @property
    def youtube_api_key(self) -> str:
        keys = self.youtube_api_keys_list
        return keys[0] if keys else ""

    @property
    def youtube_api_keys_list(self) -> list[str]:
        if not self.youtube_api_keys:
            return []
        return [k.strip() for k in self.youtube_api_keys.split(",") if k.strip()]

    def _resolve_jwt_secret(self) -> None:
        if self.jwt_secret_key:
            return

        if self.env.lower() == "prod":
            return

        object.__setattr__(self, "jwt_secret_key", _DEV_FALLBACK_JWT_SECRET)

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins:
            return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if self.env.lower() != "prod":
            return ["http://localhost:5173"]
        return []

    @property
    def cors_allowed_methods_list(self) -> list[str]:
        return [
            m.strip().upper() for m in self.cors_allowed_methods.split(",") if m.strip()
        ]


settings = Settings()
