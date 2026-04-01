import os
import sys
import logging
from loguru import logger

APP_ENV = os.getenv("ENV", "dev").lower()
LOG_LEVEL = "DEBUG" if APP_ENV == "dev" else "INFO"
BASE_LOG_DIR = os.path.join(os.getenv("BASE_LOG_DIR", "logs"), APP_ENV)

os.makedirs(BASE_LOG_DIR, exist_ok=True)

class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

logger.remove()
logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

logger.add(
    sys.stderr,
    level=LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>",
    enqueue=True,
    backtrace=True,
    diagnose=(APP_ENV == "dev")
)

logger.add(
    os.path.join(BASE_LOG_DIR, "access.log"),
    level="INFO",
    rotation="100 MB",
    retention="15 days",
    compression="zip",
    enqueue=True,
    encoding="utf-8",
    filter=lambda record: record["level"].no < logging.ERROR
)

logger.add(
    os.path.join(BASE_LOG_DIR, "error.log"),
    level="ERROR",
    rotation="50 MB",
    retention="90 days",
    compression="zip",
    enqueue=True,
    encoding="utf-8",
    backtrace=True,
    diagnose=True
)

__all__ = ["logger"]