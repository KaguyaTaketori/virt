import re
import html
import logging
import httpx
from app.config import settings

# 配置日志（如果在 FastAPI 中，可以直接使用 app 的 logger）
logger = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def clean_youtube_url(extracted_url: str) -> str:
    """清理 YouTube HTML 中提取的 URL 的转义字符"""
    if not extracted_url:
        return extracted_url
    return extracted_url.replace("\\u0026", "&").replace("\\/", "/")


def build_channel_url(input_str: str) -> str:
    """统一构建 YouTube 频道 URL"""
    if input_str.startswith("http"):
        return input_str
    if input_str.startswith("@"):
        return f"https://www.youtube.com/{input_str}"
    if input_str.startswith("UC") and len(input_str) >= 22:
        return f"https://www.youtube.com/channel/{input_str}"
    return f"https://www.youtube.com/{input_str}"


async def resolve_youtube_channel(input_str: str) -> str | None:
    """解析各种YouTube频道格式，返回 channel_id"""
    if not input_str:
        return None

    input_str = input_str.strip()

    # 如果已经是 channel_id 格式 (UC开头，通常是24位)
    if input_str.startswith("UC") and len(input_str) >= 22:
        return input_str

    url = build_channel_url(input_str)

    # 从页面解析 channel_id (全异步)
    try:
        channel_id = await resolve_from_page(url)
        if channel_id:
            return channel_id
    except Exception as e:
        logger.debug(f"Failed to resolve channel ID from page {url}: {e}")

    return None


async def resolve_from_page(url: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                url, headers={"User-Agent": DEFAULT_USER_AGENT}, follow_redirects=True
            )
            if resp.status_code != 200:
                return None

            html_content = resp.text

            canonical_match = re.search(
                r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[0-9a-zA-Z_-]{22})"',
                html_content,
            )
            if canonical_match:
                return canonical_match.group(1)

            og_match = re.search(
                r'<meta property="og:url" content="https://www\.youtube\.com/channel/(UC[0-9a-zA-Z_-]{22})"',
                html_content,
            )
            if og_match:
                return og_match.group(1)

            itemprop_match = re.search(
                r'itemprop="(?:channelId|identifier)" content="(UC[0-9a-zA-Z_-]{22})"',
                html_content,
            )
            if itemprop_match:
                return itemprop_match.group(1)

            owner_match = re.search(
                r'"externalId":"(UC[0-9a-zA-Z_-]{22})"', html_content
            )
            if owner_match:
                return owner_match.group(1)

            browse_match = re.search(
                r'"browseId":"(UC[0-9a-zA-Z_-]{22})"', html_content
            )
            if browse_match:
                return browse_match.group(1)

    except Exception as e:
        logger.debug(f"Resolve ID Error: {e}")

    return None


async def get_youtube_channel_info(input_str: str) -> dict | None:
    """通过 YouTube Data API 获取频道基本信息"""
    channel_id = await resolve_youtube_channel(input_str)
    if not channel_id:
        return None

    # 优先尝试 API - 获取完整信息
    if settings.youtube_api_key:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{YOUTUBE_API_BASE}/channels",
                    params={
                        "part": "snippet,brandingSettings,contentDetails",
                        "id": channel_id,
                        "key": settings.youtube_api_key,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("items", [])
                    if items:
                        item = items[0]
                        snippet = item.get("snippet", {})
                        branding = item.get("brandingSettings", {})
                        content = item.get("contentDetails", {})

                        thumbnails = snippet.get("thumbnails", {})

                        # banner 图片
                        image = branding.get("image", {})
                        banner_url = (
                            image.get("bannerTvMediumUrl")
                            or image.get("bannerTvUrl")
                            or image.get("bannerUrl")
                        )

                        # 频道描述
                        channel_description = branding.get("channel", {}).get(
                            "description"
                        ) or snippet.get("description")

                        return {
                            "title": snippet.get("title"),
                            "avatar_url": (
                                thumbnails.get("medium", {}).get("url")
                                or thumbnails.get("default", {}).get("url")
                            ),
                            "banner_url": banner_url,
                            "description": channel_description,
                            "channel_id": channel_id,
                        }
        except Exception as e:
            logger.warning(f"YouTube API Error for channel info: {e}")

    # 备用方法：从页面获取
    return await get_channel_info_from_page(input_str, channel_id)


async def get_channel_info_from_page(input_str: str, channel_id: str) -> dict | None:
    """从 YouTube 页面获取频道信息（备用方法）"""
    url = build_channel_url(input_str)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                url, headers={"User-Agent": DEFAULT_USER_AGENT}, follow_redirects=True
            )
            html_text = resp.text

            title_match = re.search(r"<title>([^<]+)</title>", html_text)
            title = None
            if title_match:
                title_full = title_match.group(1)
                title = html.unescape(title_full.replace(" - YouTube", "").strip())

            avatar_match = re.search(
                r'"avatar":{"thumbnails":\[{"url":"([^"]+)"', html_text
            )
            avatar_url = (
                clean_youtube_url(avatar_match.group(1)) if avatar_match else None
            )

            if title or avatar_url:
                return {
                    "title": title,
                    "avatar_url": avatar_url,
                    "channel_id": channel_id,
                }
    except Exception as e:
        logger.debug(f"Scraping info error for {url}: {e}")

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

                    description = item.get("snippet", {}).get(
                        "description"
                    ) or channel_branding.get("description")

                    external_links = channel_branding.get("externalLinks", {})
                    twitter_url = None
                    for link in external_links.get("links", []):
                        if link.get(
                            "title", ""
                        ).lower() == "twitter" or "twitter.com" in link.get("url", ""):
                            twitter_url = link.get("url")
                            break

                    youtube_url = f"https://www.youtube.com/channel/{channel_id}"

                    return {
                        "banner_url": banner_url,
                        "description": description,
                        "twitter_url": twitter_url,
                        "youtube_url": youtube_url,
                    }
    except Exception as e:
        logger.warning(f"YouTube API Error for details: {e}")

    return await get_channel_details_from_page(channel_id)


async def get_channel_details_from_page(channel_id: str) -> dict | None:
    url = f"https://www.youtube.com/channel/{channel_id}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                url, headers={"User-Agent": DEFAULT_USER_AGENT}, follow_redirects=True
            )
            html_text = resp.text

            banner_match = re.search(
                r'"banner":{"thumbnails":\[{"url":"([^"]+)"', html_text
            )
            banner_url = (
                clean_youtube_url(banner_match.group(1)) if banner_match else None
            )

            desc_match = re.search(r'"description":"([^"]+)"', html_text)
            description = desc_match.group(1) if desc_match else None
            if description:
                description = description.replace("\\n", "\n")
                description = html.unescape(description)

            twitter_match = re.search(
                r"https?://(?:www\.)?(?:twitter|x)\.com/([a-zA-Z0-9_]+)", html_text
            )
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
    except Exception as e:
        logger.debug(f"Scraping details error for {url}: {e}")

    return None
