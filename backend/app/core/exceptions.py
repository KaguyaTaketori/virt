from __future__ import annotations

from typing import Optional, Any


class VirtException(Exception):
    def __init__(self, message: str, code: str = "VIRT_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.code,
            "message": self.message,
        }


class ExternalAPIError(VirtException):
    def __init__(
        self,
        message: str,
        platform: str,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message, code="EXTERNAL_API_ERROR")
        self.platform = platform
        self.original_error = original_error

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.code,
            "message": self.message,
            "platform": self.platform,
        }


class BilibiliAPIError(ExternalAPIError):
    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message, platform="bilibili", original_error=original_error)


class YouTubeAPIError(ExternalAPIError):
    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message, platform="youtube", original_error=original_error)


class QuotaExceededError(VirtException):
    def __init__(self, operation: str):
        super().__init__(
            f"Quota exceeded for operation: {operation}", code="QUOTA_EXCEEDED"
        )
        self.operation = operation

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.code,
            "message": self.message,
            "operation": self.operation,
        }


__all__ = [
    "VirtException",
    "ExternalAPIError",
    "BilibiliAPIError",
    "YouTubeAPIError",
    "QuotaExceededError",
]
