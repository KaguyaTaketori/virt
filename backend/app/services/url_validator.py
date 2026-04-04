from __future__ import annotations

import ipaddress
import socket
from typing import Optional
from urllib.parse import urlparse

from fastapi import HTTPException


# ── YouTube 域名白名单 ─────────────────────────────────────────────────────────

_YOUTUBE_ALLOWED_HOSTS = frozenset({
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "m.youtube.com",
    "music.youtube.com",
    "googleapis.com",
    "www.googleapis.com",
})

# ── 私有/保留 IP 网段 ──────────────────────────────────────────────────────────

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("10.0.0.0/8"),        # RFC1918 A 类
    ipaddress.ip_network("172.16.0.0/12"),     # RFC1918 B 类
    ipaddress.ip_network("192.168.0.0/16"),    # RFC1918 C 类
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local（AWS 元数据服务）
    ipaddress.ip_network("::1/128"),           # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 私有
    ipaddress.ip_network("fe80::/10"),         # IPv6 Link-local
    ipaddress.ip_network("0.0.0.0/8"),         # 保留
    ipaddress.ip_network("100.64.0.0/10"),     # CGNAT（运营商内网）
]


def _is_private_ip(ip_str: str) -> bool:
    """检查 IP 是否在私有/保留网段内。"""
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in _PRIVATE_NETWORKS)
    except ValueError:
        return True  # 无法解析的 IP，视为危险


def validate_youtube_url(url: str) -> str:
    """
    验证 URL 是否为合法的 YouTube 地址。
    抛出 ValueError（非 HTTP 场景）或直接 raise（路由场景）。
    """
    try:
        parsed = urlparse(url)
    except Exception:
        raise ValueError(f"Invalid URL format: {url}")

    if parsed.scheme not in ("https",):
        raise ValueError(f"Only HTTPS URLs are allowed, got: {parsed.scheme}")

    host = (parsed.hostname or "").lower().lstrip(".")
    is_allowed = any(
        host == allowed or host.endswith("." + allowed)
        for allowed in _YOUTUBE_ALLOWED_HOSTS
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


def build_safe_youtube_url(input_str: str) -> Optional[str]:
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
            return validate_youtube_url(input_str)
        except ValueError:
            return None

    safe_slug = "".join(c for c in input_str if c.isalnum() or c in "-_.")
    if not safe_slug:
        return None
    return f"https://www.youtube.com/@{safe_slug}"