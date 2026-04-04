from __future__ import annotations

import secrets
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    youtube_api_key: str = ""
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

    env: str = "DEV"
    base_log_dir: str = "logs"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def __init__(self, **data):
        super().__init__(**data)
        self._resolve_jwt_secret()

    def _resolve_jwt_secret(self) -> None:
        if not self.jwt_secret_key:
            if self.env.lower() == "prod":
                pass
            else:
                auto_key = secrets.token_urlsafe(48)
                object.__setattr__(self, "jwt_secret_key", auto_key)

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins:
            return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if self.env.lower() != "prod":
            return ["http://localhost:5173"]
        return []

    @property
    def cors_allowed_methods_list(self) -> list[str]:
        return [m.strip().upper() for m in self.cors_allowed_methods.split(",") if m.strip()]


settings = Settings()