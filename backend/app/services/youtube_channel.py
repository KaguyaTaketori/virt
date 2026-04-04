import re
import html
import httpx
from typing import Optional
from app.loguru_config import logger
from app.config import settings
from app.services.url_validator import build_safe_youtube_url, validate_youtube_url

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
 
_HTTP_CLIENT_KWARGS = {
    "timeout": 10.0,
    "follow_redirects": True,
    "max_redirects": 3,
}

def clean_youtube_url(extracted_url: str) -> str:
    if not extracted_url:
        return extracted_url
    return extracted_url.replace("\\u0026", "&").replace("\\/", "/")


async def resolve_youtube_channel(input_str: str) -> str | None:
    if not input_str:
        return None
 
    input_str = input_str.strip()
 
    if input_str.startswith("UC") and len(input_str) >= 22:
        return input_str
 
    safe_url = build_safe_youtube_url(input_str)
    if not safe_url:
        logger.warning("Blocked potentially unsafe channel input: %r", input_str[:50])
        return None
 
    try:
        channel_id = await resolve_from_page(safe_url)
        return channel_id
    except Exception as e:
        logger.debug("Failed to resolve channel ID from %s: %s", safe_url, e)
        return None


async def resolve_from_page(url: str) -> str | None:
    try:
        validate_youtube_url(url)
    except ValueError as e:
        logger.warning("resolve_from_page blocked unsafe URL %r: %s", url[:80], e)
        return None
 
    try:
        async with httpx.AsyncClient(**_HTTP_CLIENT_KWARGS) as client:
            resp = await client.get(url, headers={"User-Agent": DEFAULT_USER_AGENT})
            if resp.status_code != 200:
                return None
 
            final_url = str(resp.url)
            try:
                validate_youtube_url(final_url)
            except ValueError:
                logger.warning("Redirect to unsafe URL blocked: %s", final_url[:80])
                return None
 
            html_content = resp.text
 
    except Exception as e:
        logger.debug("resolve_from_page error for %s: %s", url[:80], e)
        return None
 
    patterns = [
        r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[0-9a-zA-Z_-]{22})"',
        r'<meta property="og:url" content="https://www\.youtube\.com/channel/(UC[0-9a-zA-Z_-]{22})"',
        r'itemprop="(?:channelId|identifier)" content="(UC[0-9a-zA-Z_-]{22})"',
        r'"externalId":"(UC[0-9a-zA-Z_-]{22})"',
        r'"browseId":"(UC[0-9a-zA-Z_-]{22})"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html_content)
        if match:
            return match.group(1)
 
    return None
 


async def get_youtube_channel_info(input_str: str) -> dict | None:
    channel_id = await resolve_youtube_channel(input_str)
    if not channel_id:
        return None
 
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
                        thumbnails = snippet.get("thumbnails", {})
                        image = branding.get("image", {})
                        banner_url = (
                            image.get("bannerTvMediumUrl")
                            or image.get("bannerTvUrl")
                            or image.get("bannerUrl")
                        )
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
            logger.warning("YouTube API Error for channel info: %s", e)
 
    return await get_channel_info_from_page(input_str, channel_id)


async def get_channel_info_from_page(input_str: str, channel_id: str) -> dict | None:
    safe_url = build_safe_youtube_url(input_str)
    if not safe_url:
        return None
    try:
        async with httpx.AsyncClient(**_HTTP_CLIENT_KWARGS) as client:
            resp = await client.get(safe_url, headers={"User-Agent": DEFAULT_USER_AGENT})
            html_text = resp.text
            title_match = re.search(r"<title>([^<]+)</title>", html_text)
            title = None
            if title_match:
                title = html.unescape(
                    title_match.group(1).replace(" - YouTube", "").strip()
                )
            avatar_match = re.search(
                r'"avatar":{"thumbnails":\[{"url":"([^"]+)"', html_text
            )
            avatar_url = (
                clean_youtube_url(avatar_match.group(1)) if avatar_match else None
            )
            if title or avatar_url:
                return {"title": title, "avatar_url": avatar_url, "channel_id": channel_id}
    except Exception as e:
        logger.debug("Scraping info error: %s", e)
    return None


async def get_channel_details(channel_id: str) -> dict | None:
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
                    banner_url = image_branding.get("bannerExternalUrl") or image_branding.get("bannerImageUrl")
                    description = item.get("snippet", {}).get("description") or channel_branding.get("description")
                    external_links = channel_branding.get("externalLinks", {})
                    twitter_url = None
                    for link in external_links.get("links", []):
                        if link.get("title", "").lower() == "twitter" or "twitter.com" in link.get("url", ""):
                            twitter_url = link.get("url")
                            break
                    return {
                        "banner_url": banner_url,
                        "description": description,
                        "twitter_url": twitter_url,
                        "youtube_url": f"https://www.youtube.com/channel/{channel_id}",
                    }
    except Exception as e:
        logger.warning("YouTube API Error for details: %s", e)
    return await get_channel_details_from_page(channel_id)


async def get_channel_details_from_page(channel_id: str) -> dict | None:
    url = f"https://www.youtube.com/channel/{channel_id}"
    try:
        async with httpx.AsyncClient(**_HTTP_CLIENT_KWARGS) as client:
            resp = await client.get(url, headers={"User-Agent": DEFAULT_USER_AGENT})
            html_text = resp.text
            banner_match = re.search(r'"banner":{"thumbnails":\[{"url":"([^"]+)"', html_text)
            banner_url = clean_youtube_url(banner_match.group(1)) if banner_match else None
            desc_match = re.search(r'"description":"([^"]+)"', html_text)
            description = None
            if desc_match:
                description = html.unescape(desc_match.group(1).replace("\\n", "\n"))
            twitter_match = re.search(
                r"https?://(?:www\.)?(?:twitter|x)\.com/([a-zA-Z0-9_]+)", html_text
            )
            twitter_url = (
                f"https://twitter.com/{twitter_match.group(1)}" if twitter_match else None
            )
            return {
                "banner_url": banner_url,
                "description": description,
                "twitter_url": twitter_url,
                "youtube_url": f"https://www.youtube.com/channel/{channel_id}",
            }
    except Exception as e:
        logger.debug("Scraping details error for %s: %s", url, e)
    return None