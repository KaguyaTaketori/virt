from fastapi import APIRouter
from .crud import router as crud_router
from .videos import router as videos_router
from .bilibili import router as bilibili_router
from .scraper import router as scraper_router

router = APIRouter(prefix="/api/channels", tags=["channels"])
router.include_router(crud_router)
router.include_router(videos_router)
router.include_router(bilibili_router)
router.include_router(scraper_router)