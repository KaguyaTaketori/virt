from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    youtube_api_key: str = ""
    bilibili_sessdata: str = ""
    db_url: str = "sqlite:///./streams.db"
    enable_danmaku: bool = False
    danmaku_storage_path: str = "./danmaku_data"
    admin_secret_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
