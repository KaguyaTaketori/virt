from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse
from typing import Optional

from app.loguru_config import logger

_SCHEME_WHITELIST = frozenset({"https"}) 

_YOUTUBE_ALLOWED_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "youtu.be",
        "m.youtube.com",
        "music.youtube.com",
        "googleapis.com",
        "www.googleapis.com",
    }
)

_BILIBILI_ALLOWED_HOSTS = frozenset(
    {
        "bilibili.com",
        "www.bilibili.com",
        "live.bilibili.com",
        "space.bilibili.com",
        "player.bilibili.com",
    }
)

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
]


def _is_private_ip(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in _PRIVATE_NETWORKS)
    except ValueError:
        return True


def validate_safe_url(
    url: str,
    allowed_hosts: Optional[set[str]] = None,
    *,
    allow_http: bool = False,
) -> str:
    """
    验证 URL 是否为合法的公开地址（非私有/保留网段）。
    抛出 ValueError 如果不安全。
    """
    allowed_schemes = {"https", "http"} if allow_http else _SCHEME_WHITELIST
    try:
        parsed = urlparse(url)
    except Exception:
        raise ValueError(f"Invalid URL format: {url}")

    if parsed.scheme not in allowed_schemes:
        raise ValueError(f"Only {allowed_schemes} URLs allowed: {parsed.scheme}")

    host = (parsed.hostname or "").lower().lstrip(".")

    if allowed_hosts:
        is_allowed = any(
            host == allowed or host.endswith("." + allowed) for allowed in allowed_hosts
        )
        if not is_allowed:
            raise ValueError(f"Domain not in allowlist: {host}")

    try:
        resolved_ips = socket.getaddrinfo(host, None)
        for _, _, _, _, sockaddr in resolved_ips:
            ip_str = sockaddr[0]
            if _is_private_ip(ip_str):
                raise ValueError(
                    f"Domain {host} resolves to private IP {ip_str}, blocked for security"
                )
    except socket.gaierror:
        raise ValueError(f"Cannot resolve domain: {host}")

    return url


def build_youtube_url(input_str: str) -> Optional[str]:
    """
    从任意输入构建安全的 YouTube URL。
    支持: UCxxx, @handle, https://..., plain string
    """
    if not input_str:
        return None

    input_str = input_str.strip()

    if input_str.startswith("UC") and len(input_str) >= 22:
        return f"https://www.youtube.com/channel/{input_str}"

    if input_str.startswith("@"):
        handle = input_str.lstrip("@")
        if not handle.replace("-", "").replace("_", "").replace(".", "").isalnum():
            return None
        return f"https://www.youtube.com/@{handle}"

    if input_str.startswith("http"):
        try:
            return validate_safe_url(input_str, allowed_hosts=_YOUTUBE_ALLOWED_HOSTS)
        except ValueError:
            return None

    safe_slug = "".join(c for c in input_str if c.isalnum() or c in "-_.")
    if not safe_slug:
        return None
    return f"https://www.youtube.com/@{safe_slug}"


def build_bilibili_url(input_str: str) -> Optional[str]:
    """
    从任意输入构建安全的 Bilibili URL。
    支持: 数字UID, https://space.bilibili.com/xxx
    """
    if not input_str:
        return None

    input_str = input_str.strip()

    if input_str.isdigit():
        return f"https://space.bilibili.com/{input_str}"

    if input_str.startswith("https://space.bilibili.com/"):
        parts = input_str.split("/")
        if len(parts) >= 4:
            uid = parts[-1].split("?")[0]
            if uid.isdigit():
                try:
                    return validate_safe_url(
                        input_str, allowed_hosts=_BILIBILI_ALLOWED_HOSTS
                    )
                except ValueError:
                    return None

    if input_str.startswith("BV"):
        return f"https://www.bilibili.com/video/{input_str}"

    return None


class IframeUrlGenerator:
    """
    生成安全的 iframe 嵌入 URL。
    自动处理不同平台的 video ID 格式转换。
    """

    @staticmethod
    def for_youtube(video_id: str) -> str:
        """生成 YouTube embed URL"""
        vid = video_id
        if video_id.startswith("https://"):
            import re

            match = re.search(r"(?:v=|/v/)([a-zA-Z0-9_-]{11})", video_id)
            if match:
                vid = match.group(1)
        elif len(video_id) == 11:
            vid = video_id

        return f"https://www.youtube.com/embed/{vid}"

    @staticmethod
    def for_bilibili(video_id: str) -> str:
        """生成 Bilibili embed URL"""
        bvid = video_id
        if video_id.startswith("BV"):
            bvid = video_id
        elif video_id.startswith("https://") or video_id.startswith("http://"):
            import re

            match = re.search(r"bvid=([A-Za-z0-9]{10})", video_id)
            if match:
                bvid = match.group(1)
            else:
                match = re.search(r"/video/([A-Za-z0-9]{10})", video_id)
                if match:
                    bvid = match.group(1)

        return f"https://player.bilibili.com/player.html?bvid={bvid}&autoplay=0"

    @staticmethod
    def generate(platform: str, video_id: str) -> str:
        """通用的 embed URL 生成"""
        if platform == "youtube":
            return IframeUrlGenerator.for_youtube(video_id)
        elif platform == "bilibili":
            return IframeUrlGenerator.for_bilibili(video_id)
        else:
            raise ValueError(f"Unknown platform: {platform}")
