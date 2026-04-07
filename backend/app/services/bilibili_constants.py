# backend/app/services/bilibili_constants.py
from typing import Final

BILIBILI_LIVE_API: Final[str] = "https://api.live.bilibili.com"
BILIBILI_API: Final[str] = "https://api.bilibili.com"

BACKOFF_INIT: Final[int] = 60
BACKOFF_MAX: Final[int] = 600
BACKOFF_FACTOR: Final[int] = 2
MAX_RETRIES: Final[int] = 3
BATCH_SIZE: Final[int] = 15
BATCH_SLEEP_MIN: Final[float] = 3.0
BATCH_SLEEP_MAX: Final[float] = 5.0
REQ_SLEEP_MIN: Final[float] = 1.0
REQ_SLEEP_MAX: Final[float] = 2.2

BASE_HEADERS: Final[dict] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.bilibili.com/",
    "Origin": "https://www.bilibili.com",
}
