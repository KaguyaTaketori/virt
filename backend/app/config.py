from pydantic_settings import BaseSettings
from typing import Optional


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

    env: str = "DEV"
    base_log_dir: str = "logs"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
