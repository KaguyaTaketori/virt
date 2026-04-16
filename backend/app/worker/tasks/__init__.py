from __future__ import annotations

from app.worker.tasks.bilibili import update_bilibili_streams
from app.worker.tasks.youtube import (
    update_youtube_streams,
    sync_youtube_videos_incremental,
    sync_youtube_videos_full,
    discover_live_streams_from_videos,
    refresh_channel_details,
    daily_backfill_sync,
)
from app.worker.tasks.websub import renew_websub
from app.worker.tasks.scraper import scheduled_scrape_all

__all__ = [
    "update_bilibili_streams",
    "update_youtube_streams",
    "sync_youtube_videos_incremental",
    "sync_youtube_videos_full",
    "discover_live_streams_from_videos",
    "refresh_channel_details",
    "daily_backfill_sync",
    "renew_websub",
    "scheduled_scrape_all",
]
