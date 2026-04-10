from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import STATE_STOPPED
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.loguru_config import logger
from app.worker.locks import RedisLock


def _create_trigger(trigger_type: str, **kwargs) -> Any:
    """创建 APScheduler 触发器。"""
    if trigger_type == "interval":
        return IntervalTrigger(**kwargs)
    elif trigger_type == "cron":
        return CronTrigger(**kwargs)
    else:
        raise ValueError(f"Unknown trigger type: {trigger_type}")


class WorkerScheduler:
    """Worker 调度器。封装 APScheduler，提供任务管理和分布式锁支持。"""

    def __init__(self, timezone_: str = "UTC"):
        self.scheduler = AsyncIOScheduler(timezone=timezone_)
        self._started = False
        self._job_defaults = {
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 300,
        }

    @property
    def is_started(self) -> bool:
        return self._started

    def add_interval_job(
        self,
        func: Callable,
        job_id: str,
        minutes: Optional[int] = None,
        seconds: Optional[int] = None,
        hours: Optional[int] = None,
        **kwargs,
    ) -> None:
        """添加 Interval 任务。"""
        trigger_kwargs = {}
        if minutes is not None:
            trigger_kwargs["minutes"] = minutes
        if seconds is not None:
            trigger_kwargs["seconds"] = seconds
        if hours is not None:
            trigger_kwargs["hours"] = hours

        trigger = _create_trigger("interval", **trigger_kwargs)

        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            **self._job_defaults,
            **kwargs,
        )
        logger.debug(
            "Registered interval job: %s (interval=%s)", job_id, trigger_kwargs
        )

    def add_cron_job(
        self,
        func: Callable,
        job_id: str,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
        day_of_week: Optional[str] = None,
        **kwargs,
    ) -> None:
        """添加 Cron 任务。"""
        trigger_kwargs = {}
        if hour is not None:
            trigger_kwargs["hour"] = hour
        if minute is not None:
            trigger_kwargs["minute"] = minute
        if day_of_week is not None:
            trigger_kwargs["day_of_week"] = day_of_week

        trigger = _create_trigger("cron", **trigger_kwargs)

        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            **self._job_defaults,
            **kwargs,
        )
        logger.debug("Registered cron job: %s (cron=%s)", job_id, trigger_kwargs)

    def add_job(
        self,
        func: Callable,
        trigger_type: str,
        job_id: str,
        **trigger_kwargs,
    ) -> None:
        """通用添加任务方法。"""
        trigger = _create_trigger(trigger_type, **trigger_kwargs)

        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            **self._job_defaults,
        )
        logger.debug("Registered job: %s (%s)", job_id, trigger_type)

    def remove_job(self, job_id: str) -> bool:
        """移除任务。"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info("Removed job: %s", job_id)
            return True
        except Exception:
            return False

    def get_job(self, job_id: str) -> Optional[Any]:
        """获取任务。"""
        return self.scheduler.get_job(job_id)

    def list_jobs(self) -> list[dict[str, Any]]:
        """列出所有任务。"""
        jobs = self.scheduler.get_jobs()
        return [
            {
                "id": job.id,
                "next_run_time": job.next_run_time,
                "trigger": str(job.trigger),
            }
            for job in jobs
        ]

    def start(self) -> None:
        """启动调度器。"""
        if self.scheduler.state != STATE_STOPPED:
            logger.warning("Scheduler already running")
            return

        self.scheduler.start()
        self._started = True
        logger.info("Worker scheduler started")

    def shutdown(self, wait: bool = True) -> None:
        """停止调度器。"""
        if self.scheduler.state == STATE_STOPPED:
            return

        self.scheduler.shutdown(wait=wait)
        self._started = False
        logger.info("Worker scheduler stopped")


worker_scheduler = WorkerScheduler()


class PeriodicTaskRunner:
    """带幂等性检查的任务运行器。"""

    def __init__(self, task_id: str, lock_timeout: int = 300):
        self.task_id = task_id
        self.lock_timeout = lock_timeout

    async def run(self, func: Callable, *args, **kwargs) -> bool:
        """运行任务，使用分布式锁确保幂等性。"""
        async with RedisLock.acquire_lock(
            f"task:{self.task_id}",
            timeout=self.lock_timeout,
        ) as acquired:
            if not acquired:
                logger.info("Task %s skipped (already running)", self.task_id)
                return False

            try:
                await func(*args, **kwargs)
                logger.info("Task %s completed", self.task_id)
                return True
            except Exception as e:
                logger.error("Task %s failed: %s", self.task_id, e)
                return False


def run_with_lock(task_id: str, func: Callable, *args, **kwargs) -> bool:
    """简化的带锁任务运行。"""
    runner = PeriodicTaskRunner(task_id)
    return runner.run(func, *args, **kwargs)
