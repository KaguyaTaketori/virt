from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session
from app.deps.guards import ChannelManage
from app.loguru_config import logger
from app.services.scraper import sync as scraper_sync

router = APIRouter(
    tags=["scraper"],
    dependencies=[ChannelManage],
)


@router.post("/scrape/vspo")
async def scrape_vspo(db: AsyncSession = Depends(get_db_session)):
    try:
        result = await scraper_sync.scrape_and_sync_vspo(db)
        return {"status": "success", "source": "vspo", **result}
    except Exception as e:
        logger.error("scrape_vspo error: {}", e)
        raise HTTPException(status_code=500, detail="爬取 VSPO! 失败")


@router.post("/scrape/nijisanji")
async def scrape_nijisanji(db: AsyncSession = Depends(get_db_session)):
    try:
        result = await scraper_sync.scrape_and_sync_nijisanji(db)
        return {"status": "success", "source": "nijisanji", **result}
    except Exception as e:
        logger.error("scrape_nijisanji error: {}", e)
        raise HTTPException(status_code=500, detail="爬取 Nijisanji 失败")


@router.post("/scrape/all")
async def scrape_all(db: AsyncSession = Depends(get_db_session)):
    try:
        result = await scraper_sync.scrape_and_sync_all(db)
        return {"status": "success", **result}
    except Exception as e:
        logger.error("scrape_all error: {}", e)
        raise HTTPException(status_code=500, detail="爬取失败")