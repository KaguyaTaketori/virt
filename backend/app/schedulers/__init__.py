from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import STATE_STOPPED
from app.loguru_config import logger

from .youtube import (
    update_youtube_streams,
    sync_youtube_videos_full,
    discover_live_streams_from_videos,
)
from .bilibili import update_bilibili_streams
from .maintenance import (
    refresh_channel_details,
    daily_backfill_sync,
    renew_websub,
)
from .scraper import scheduled_scrape_all

scheduler = AsyncIOScheduler(timezone="UTC")


def start_scheduler() -> None:
    if scheduler.state != STATE_STOPPED:
        return

    now = datetime.now(timezone.utc)

    scheduler.add_job(
        update_youtube_streams,
        "interval",
        minutes=5,
        id="yt_update",
        replace_existing=True,
    )
    scheduler.add_job(
        update_bilibili_streams,
        "interval",
        minutes=2,
        id="bili_update",
        next_run_time=now,
        replace_existing=True,
    )
    scheduler.add_job(
        refresh_channel_details,
        "interval",
        hours=24,
        id="channel_refresh",
        next_run_time=now,
        replace_existing=True,
    )
    scheduler.add_job(
        sync_youtube_videos_full,
        "cron",
        hour=3,
        minute=0,
        id="yt_full_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        discover_live_streams_from_videos,
        "interval",
        minutes=5,
        id="yt_live_discover",
        replace_existing=True,
    )
    scheduler.add_job(
        daily_backfill_sync,
        "cron",
        hour=4,
        minute=0,
        id="daily_backfill",
        replace_existing=True,
    )
    scheduler.add_job(
        renew_websub, "interval", days=8, id="websub_renew", replace_existing=True
    )
    scheduler.add_job(
        scheduled_scrape_all,
        "cron",
        hour=2,
        minute=0,
        day_of_week=6,
        id="wiki_scrape_weekly",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Scheduler started | "
        "yt_update=5min | bili_update=2min | yt_full_sync=03:00 | "
        "yt_live_discover=5min | daily_backfill=04:00 | "
        "websub_renew=8d | wiki_scrape=Sun 02:00"
    )
