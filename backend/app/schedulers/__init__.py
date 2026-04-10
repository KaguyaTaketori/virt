"""
Backward compatibility: Re-export from worker/tasks
"""

from app.worker.tasks import (
    update_bilibili_streams,
    update_youtube_streams,
    sync_youtube_videos_incremental,
    sync_youtube_videos_full,
    discover_live_streams_from_videos,
    refresh_channel_details,
    daily_backfill_sync,
    renew_websub,
    scheduled_scrape_all,
    BaseTask,
    IntervalTask,
    CronTask,
    TaskRegistry,
    register_task,
)
from app.worker.scheduler import worker_scheduler as scheduler


def start_scheduler():
    """Start the scheduler - now handled by startup.py"""
    pass


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
    "start_scheduler",
    "scheduler",
    "BaseTask",
    "IntervalTask",
    "CronTask",
    "TaskRegistry",
    "register_task",
]
