from __future__ import annotations


class BilibiliAPIError(Exception):
    """Bilibili API 基础异常"""

    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


class BilibiliRateLimitedError(BilibiliAPIError):
    """触发 412 风控限流，可重试"""

    def __init__(self, uid: str, backoff: int):
        super().__init__(f"Rate limited uid={uid}, backoff={backoff}s", retryable=True)
        self.uid = uid
        self.backoff = backoff


class BilibiliNotFoundError(BilibiliAPIError):
    """资源不存在，不可重试"""

    def __init__(self, uid: str):
        super().__init__(f"User not found uid={uid}", retryable=False)
        self.uid = uid


class BilibiliNetworkError(BilibiliAPIError):
    """网络错误，可重试"""

    def __init__(self, uid: str, original: Exception):
        super().__init__(f"Network error uid={uid}: {original}", retryable=True)
        self.uid = uid
        self.original = original
