from app.services.scraper.sync import scrape_and_sync_all
from app.database_async import AsyncSessionFactory


async def scheduled_scrape_all():
    """定时任务：爬取并同步所有VTuber Wiki"""
    async with AsyncSessionFactory() as db:
        return await scrape_and_sync_all(db)