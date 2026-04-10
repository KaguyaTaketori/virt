import asyncio
from typing import Optional
from app.loguru_config import logger

class ApiKeyManager:
    def __init__(self) -> None:
        self._keys: list[str] = []
        self._current_index: int = 0
        self._lock = asyncio.Lock()

    def initialize(self, keys: list[str]) -> None:
        self._keys = [k for k in keys if k]

    async def get_current_key(self) -> Optional[str]:
        if not self._keys:
            return None
        async with self._lock:
            return self._keys[self._current_index]

    async def mark_key_failed(self, key: str) -> bool:
        if not self._keys:
            return False

        async with self._lock:
            try:
                failed_idx = self._keys.index(key)
            except ValueError:
                return False

            next_idx = (failed_idx + 1) % len(self._keys)

            if next_idx == failed_idx:
                logger.error("仅有一个 API key 且已失败，无法轮转")
                return False

            self._current_index = next_idx
            new_key = self._keys[self._current_index]
            logger.info(
                "API key 轮转成功: {} -> {} (index={})",
                key[:10] + "...", new_key[:10] + "...", self._current_index
            )
            return True

    async def is_available(self) -> bool:
        return bool(self._keys)

api_key_manager = ApiKeyManager()

async def get_api_key() -> Optional[str]:
    return await api_key_manager.get_current_key()

async def mark_key_failed(key: str) -> bool:
    return await api_key_manager.mark_key_failed(key)

async def is_api_available() -> bool:
    return await api_key_manager.is_available()