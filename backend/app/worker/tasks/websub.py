from __future__ import annotations

from app.config import settings
from app.integrations.websub.subscription_service import websub_service
from app.loguru_config import logger


async def renew_websub() -> None:
    if (
        not settings.websub_callback_url
        or settings.websub_callback_url == "https://your-domain.com/api/websub/youtube"
    ):
        return

    try:
        await websub_service.subscribe_all_active(settings.websub_callback_url)
        logger.info("WebSub 订阅刷新完成")
    except Exception as e:
        logger.error("WebSub 订阅刷新失败: {}", e)
