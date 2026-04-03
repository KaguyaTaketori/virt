import os
import sys
from loguru import logger
from app.config import settings

APP_ENV = settings.env.lower()
LOG_LEVEL = "DEBUG" if APP_ENV == "dev" else "INFO"
BASE_LOG_DIR = os.path.join(settings.base_log_dir, APP_ENV)

os.makedirs(BASE_LOG_DIR, exist_ok=True)

logger.remove()

logger.add(
    sys.stderr,
    level=LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    colorize=True,
)

logger.add(
    os.path.join(BASE_LOG_DIR, "app.log"),
    level="INFO",
    rotation="100 MB",
    retention="15 days",
    encoding="utf-8",
)

__all__ = ["logger"]