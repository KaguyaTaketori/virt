from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    youtube_api_key: str = ""
    bilibili_sessdata: str = ""   # 可选，B站账号 cookie
    db_url: str = "sqlite:///./streams.db"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
