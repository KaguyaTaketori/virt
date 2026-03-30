import re
import subprocess
import httpx
from app.config import settings


YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def resolve_youtube_channel(input_str: str) -> str | None:
    """解析各种YouTube频道格式，返回channel_id"""
    if not input_str:
        return None

    # 清理输入
    input_str = input_str.strip()

    # 如果已经是 channel_id 格式 (UC开头)
    if input_str.startswith("UC") and len(input_str) >= 22:
        return input_str

    # 转换为完整 URL
    url = input_str
    if input_str.startswith("@"):
        username = input_str[1:]
        url = f"https://www.youtube.com/@{username}"
    elif not input_str.startswith("http"):
        url = f"https://www.youtube.com/{input_str}"

    # 直接从页面解析 channel_id（更快）
    try:
        channel_id = resolve_from_page(url)
        if channel_id:
            return channel_id
    except Exception:
        pass  # 静默失败

    return None


def resolve_from_page(url: str) -> str | None:
    """从 YouTube 页面获取 channel_id"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = httpx.get(url, headers=headers, timeout=10.0)
        html = resp.text

        # 查找 channel_id (已经是完整 UC 格式)
        patterns = [
            r'"channelId":"(UC[0-9a-zA-Z_-]{22})"',
            r'"externalId":"(UC[0-9a-zA-Z_-]{22})"',
            r"channel_id=(UC[0-9a-zA-Z_-]{22})",
        ]

        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)

    except Exception as e:
        pass  # 静默

    return None


async def get_youtube_channel_info(input_str: str) -> dict | None:
    """通过 YouTube Data API 获取频道信息"""
    channel_id = resolve_youtube_channel(input_str)
    if not channel_id:
        return None

    # 优先尝试 API
    if settings.youtube_api_key:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{YOUTUBE_API_BASE}/channels",
                    params={
                        "part": "snippet",
                        "id": channel_id,
                        "key": settings.youtube_api_key,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("items", [])
                    if items:
                        snippet = items[0].get("snippet", {})
                        thumbnails = snippet.get("thumbnails", {})
                        return {
                            "title": snippet.get("title"),
                            "avatar_url": thumbnails.get("medium", {}).get("url")
                            or thumbnails.get("default", {}).get("url"),
                            "channel_id": channel_id,
                        }
        except Exception:
            pass  # 静默

    # 备用方法：从页面获取
    return await get_channel_info_from_page(input_str, channel_id)


async def get_channel_info_from_page(input_str: str, channel_id: str) -> dict | None:
    """从 YouTube 页面获取频道信息（备用方法）"""
    # 构建 URL
    if input_str.startswith("@"):
        url = f"https://www.youtube.com/{input_str}"
    elif not input_str.startswith("http"):
        url = f"https://www.youtube.com/{input_str}"
    else:
        url = input_str

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            html = resp.text

            # 提取 title (从 <title> 标签)
            title_match = re.search(r"<title>([^<]+)</title>", html)
            title = None
            if title_match:
                title_full = title_match.group(1)
                # 移除 " - YouTube" 后缀
                title = title_full.replace(" - YouTube", "").strip()

            # 提取 avatar (从 ytInitialData)
            avatar_match = re.search(r'"avatar":{"thumbnails":\[{"url":"([^"]+)"', html)
            avatar_url = avatar_match.group(1) if avatar_match else None

            if title or avatar_url:
                return {
                    "title": title,
                    "avatar_url": avatar_url,
                    "channel_id": channel_id,
                }
    except Exception:
        pass  # 静默

    return None


async def get_channel_details(channel_id: str) -> dict | None:
    """通过 YouTube Data API 获取频道详细信息: banner, description, externalLinks"""
    if not settings.youtube_api_key:
        return await get_channel_details_from_page(channel_id)

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{YOUTUBE_API_BASE}/channels",
                params={
                    "part": "brandingSettings,snippet",
                    "id": channel_id,
                    "key": settings.youtube_api_key,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                if items:
                    item = items[0]
                    branding = item.get("brandingSettings", {})
                    channel_branding = branding.get("channel", {})
                    image_branding = branding.get("image", {})

                    banner_url = image_branding.get(
                        "bannerExternalUrl"
                    ) or image_branding.get("bannerImageUrl")

                    description = channel_branding.get("description")

                    external_links = channel_branding.get("externalLinks", {})
                    twitter_url = None
                    for link in external_links.get("links", []):
                        if link.get("title", "").lower() == "twitter":
                            twitter_url = link.get("url")
                            break

                    youtube_url = f"https://www.youtube.com/channel/{channel_id}"

                    return {
                        "banner_url": banner_url,
                        "description": description,
                        "twitter_url": twitter_url,
                        "youtube_url": youtube_url,
                    }
    except Exception:
        pass

    return await get_channel_details_from_page(channel_id)


async def get_channel_details_from_page(channel_id: str) -> dict | None:
    """从 YouTube 频道页面获取详细信息（备用方法）"""
    url = f"https://www.youtube.com/channel/{channel_id}"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            html = resp.text

            banner_match = re.search(r'"banner":{"thumbnails":\[{"url":"([^"]+)"', html)
            banner_url = banner_match.group(1) if banner_match else None

            desc_match = re.search(r'"description":"([^"]+)"', html)
            description = desc_match.group(1) if desc_match else None
            if description:
                description = description.replace("\\n", "\n")

            twitter_match = re.search(r"twitter\.com/([a-zA-Z0-9_]+)", html)
            twitter_url = (
                f"https://twitter.com/{twitter_match.group(1)}"
                if twitter_match
                else None
            )

            youtube_url = f"https://www.youtube.com/channel/{channel_id}"

            return {
                "banner_url": banner_url,
                "description": description,
                "twitter_url": twitter_url,
                "youtube_url": youtube_url,
            }
    except Exception:
        pass

    return None
