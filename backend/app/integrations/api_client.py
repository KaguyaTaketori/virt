from __future__ import annotations

import asyncio
from typing import Any, Optional

import httpx

from app.loguru_config import logger

DEFAULT_TIMEOUT = 15.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 1.0
DEFAULT_BACKOFF_MAX = 30.0


class BaseAPIClient:
    """
    统一 HTTP 客户端封装。
    特性：
    - 连接池复用（类级别 AsyncClient）
    - 指数退避重试（默认 3 次）
    - 统一超时（默认 15s）
    - 统一日志与错误处理
    """

    _client: Optional[httpx.AsyncClient] = None

    def __init__(
        self,
        base_url: str,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
        backoff_max: float = DEFAULT_BACKOFF_MAX,
        headers: Optional[dict[str, str]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self._headers = headers or {}

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        """获取或创建共享的 AsyncClient（连接池复用）"""
        if cls._client is None or cls._client.is_closed:
            cls._client = httpx.AsyncClient(
                timeout=httpx.Timeout(DEFAULT_TIMEOUT),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
                follow_redirects=True,
                max_redirects=3,
            )
        return cls._client

    @classmethod
    async def close_client(cls) -> None:
        """应用关闭时调用，清理连接池"""
        if cls._client is not None and not cls._client.is_closed:
            await cls._client.aclose()
            cls._client = None
            logger.info("BaseAPIClient connection pool closed")

    async def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        统一的请求方法，含指数退避重试。
        """
        url = f"{self.base_url}{path}"
        backoff = self.backoff_base

        headers = {**self._headers, **kwargs.pop("headers", {})}

        for attempt in range(self.max_retries):
            try:
                client = self.get_client()
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs,
                )
                if response.status_code < 400:
                    return response

                if response.status_code >= 500:
                    logger.warning(
                        "HTTP {} {}, retry {}/{}",
                        response.status_code,
                        url,
                        attempt + 1,
                        self.max_retries,
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, self.backoff_max)
                        continue

                return response

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                logger.warning(
                    "HTTP request error: {}, retry {}/{}",
                    e,
                    attempt + 1,
                    self.max_retries,
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, self.backoff_max)
                    continue
                raise

            except Exception as e:
                logger.error("HTTP request unexpected error: {}", e)
                raise

        raise RuntimeError(f"HTTP request failed after {self.max_retries} retries")

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("DELETE", path, **kwargs)


class BilibiliAPIClient(BaseAPIClient):
    """Bilibili API 专用客户端"""

    def __init__(self):
        super().__init__(
            base_url="https://api.bilibili.com",
            timeout=15.0,
            max_retries=3,
        )
        self._sessdata: Optional[str] = None

    def set_credential(self, sessdata: str) -> None:
        self._sessdata = sessdata

    def _build_headers(self, credential: Optional[Any] = None) -> dict[str, str]:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if self._sessdata:
            headers["Cookie"] = f"SESSDATA={self._sessdata}"
        return headers


class YouTubeAPIClient(BaseAPIClient):
    """YouTube API 专用客户端"""

    def __init__(self):
        super().__init__(
            base_url="https://www.googleapis.com/youtube/v3",
            timeout=15.0,
            max_retries=3,
        )
        self._api_key: Optional[str] = None
        self._user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    def set_api_key(self, api_key: str) -> None:
        self._api_key = api_key

    def _build_headers(self) -> dict[str, str]:
        return {"User-Agent": self._user_agent}
