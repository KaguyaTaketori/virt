import asyncio
from typing import Optional

import httpx

from app.config import settings
from app.loguru_config import logger

_api_keys: list[str] = []
_current_key_index: int = 0
_lock = asyncio.Lock()


def _init_keys() -> list[str]:
    global _api_keys
    if not _api_keys:
        _api_keys = settings.youtube_api_keys_list
    return _api_keys


async def get_api_key() -> Optional[str]:
    keys = _init_keys()
    if not keys:
        return None
    async with _lock:
        return keys[_current_key_index]


async def get_all_api_keys() -> list[str]:
    keys = _init_keys()
    return keys.copy()


async def get_current_key_index() -> int:
    await _init_keys()
    async with _lock:
        return _current_key_index


async def mark_key_failed(key: str) -> bool:
    keys = _init_keys()
    if not keys:
        return False

    async with _lock:
        failed_idx = -1
        for i, k in enumerate(keys):
            if k == key:
                failed_idx = i
                break

        if failed_idx == -1:
            return False

        logger.warning(
            "API key {} 失败 (index={}), 尝试切换到下一个", key[:10] + "...", failed_idx
        )

        next_idx = (failed_idx + 1) % len(keys)
        if next_idx == 0 and _current_key_index == 0:
            logger.error("所有 API keys 都已失败")
            return False

        _current_key_index = next_idx
        new_key = keys[_current_key_index]
        logger.info(
            "切换到 API key {} (index={})", new_key[:10] + "...", _current_key_index
        )
        return True


async def is_api_available() -> bool:
    keys = _init_keys()
    return len(keys) > 0


class APIKeyRotationMiddleware:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    def _is_403_error(self, response: httpx.Response) -> bool:
        if response.status_code == 403:
            return True
        return False

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        keys = _init_keys()
        if not keys:
            raise ValueError("No API keys configured")

        last_exception: Optional[Exception] = None
        tried_keys: set[int] = set()

        for _ in range(len(keys)):
            idx = await get_current_key_index()
            if idx in tried_keys:
                break
            tried_keys.add(idx)

            key = keys[idx]
            if "params" in kwargs:
                kwargs["params"] = {**kwargs["params"], "key": key}
            else:
                kwargs["params"] = {"key": key}

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.request(method, url, **kwargs)
                    if self._is_403_error(resp):
                        await mark_key_failed(key)
                        continue
                    return resp
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    await mark_key_failed(key)
                    continue
                raise
            except Exception as e:
                logger.warning("API request failed with {}: {}", type(e).__name__, e)
                await mark_key_failed(key)
                continue

        raise ValueError("All API keys failed")


api_key_manager = APIKeyRotationMiddleware()
