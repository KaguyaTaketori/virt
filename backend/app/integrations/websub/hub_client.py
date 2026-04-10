import httpx
from app.loguru_config import logger

_HUB_URL   = "https://pubsubhubbub.appspot.com/"
_TOPIC_BASE = "https://www.youtube.com/xml/feeds/videos.xml?channel_id="

class HubClient:
    async def subscribe(
        self,
        channel_youtube_id: str,
        callback_url: str,
        *,
        mode: str = "subscribe",
        lease_seconds: int = 9 * 86400,
        secret: str = "",
    ) -> bool:
        topic_url = f"{_TOPIC_BASE}{channel_youtube_id}"
        payload = {
            "hub.callback":      callback_url,
            "hub.mode":          mode,
            "hub.topic":         topic_url,
            "hub.lease_seconds": str(lease_seconds),
            "hub.verify":        "async",
        }
        if secret:
            payload["hub.secret"] = secret

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(_HUB_URL, data=payload)
            success = resp.status_code == 202
            if not success:
                logger.warning("Hub 拒绝 {} | status={}", mode, resp.status_code)
            return success
        except httpx.RequestError as e:
            logger.error("Hub 请求失败: {}", e)
            return False

hub_client = HubClient()