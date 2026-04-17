from __future__ import annotations

from app.services.scraper.sync import scrape_and_sync_all
from app.loguru_config import logger
from app.database.session import session_scope


async def scheduled_scrape_all() -> None:
    try:
        async with session_scope() as db:
            result = await scrape_and_sync_all(db)
            logger.info("定时爬取完成: {}", result)
    except Exception as e:
        logger.error("定时爬取失败: {}", e)