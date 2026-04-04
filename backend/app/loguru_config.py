import logging
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
    enqueue=True,
)

logger.add(
    os.path.join(BASE_LOG_DIR, "error.log"),
    level="ERROR",
    rotation="50 MB",
    retention="30 days",
    encoding="utf-8",
    enqueue=True,
)


logger.add(
    os.path.join(BASE_LOG_DIR, "access.log"),
    level="INFO",
    rotation="100 MB",
    retention="7 days",
    encoding="utf-8",
    filter=lambda record: "access" in record["extra"],
    enqueue=True,
)

class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 找到调用位置
        frame, depth = logging.currentframe(), 2
        while frame and (frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, f"[{record.name}] {record.getMessage()}"
        )

def setup_logging():
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    silent_loggers = [
        "sqlalchemy.engine", 
        "sqlalchemy.pool",
        "httpx",
        "httpcore",
        "aiosqlite",
        "uvicorn",
        "uvicorn.access",
        "apscheduler",
    ]

    for logger_name in silent_loggers:
        _logger = logging.getLogger(logger_name)
        _logger.setLevel(logging.WARNING)
        _logger.handlers = [InterceptHandler()]
        _logger.propagate = False

    logging.getLogger("uvicorn").handlers = [InterceptHandler()]

setup_logging()

__all__ = ["logger"]