from __future__ import annotations

from app.services.scraper.sync import scrape_and_sync_all
from app.loguru_config import logger


async def scheduled_scrape_all() -> None:
    try:
        await scrape_and_sync_all()
        logger.info("定时爬取完成")
    except Exception as e:
        logger.error("定时爬取失败: {}", e)
