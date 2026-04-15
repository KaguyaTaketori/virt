from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, FrozenSet, Optional

import httpx
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import STATE_STOPPED

from app.loguru_config import logger

DEFAULT_REDIS_HOST = "localhost"
DEFAULT_REDIS_PORT = 6379
DEFAULT_REDIS_DB = 0


class SchedulerService:
    """
    统一调度服务。
    - 使用 RedisJobStore 实现分布式任务持久化
    - 支持 Interval、Cron、Date 触发器
    - 与应用生命周期解耦
    """

    def __init__(
        self,
        redis_host: str = DEFAULT_REDIS_HOST,
        redis_port: int = DEFAULT_REDIS_PORT,
        redis_db: int = DEFAULT_REDIS_DB,
    ):
        self._redis_host = redis_host
        self._redis_port = redis_port
        self._redis_db = redis_db
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._job_defaults = {
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 300,
        }

    @property
    def is_started(self) -> bool:
        return self._scheduler is not None and self._scheduler.state != STATE_STOPPED

    @property
    def scheduler(self) -> AsyncIOScheduler:
        return self._scheduler

    def _get_jobstore(self) -> RedisJobStore:
        return RedisJobStore(
            host=self._redis_host,
            port=self._redis_port,
            db=self._redis_db,
        )

    async def start(self) -> None:
        """启动调度器（需要 Redis）"""
        if self.is_started:
            logger.warning("Scheduler already running")
            return

        try:
            self._scheduler = AsyncIOScheduler(
                jobstores={"default": self._get_jobstore()},
                job_defaults=self._job_defaults,
                timezone="UTC",
            )
            self._scheduler.start()
            logger.info("Scheduler started with RedisJobStore")
        except Exception as e:
            logger.error("Failed to start scheduler: {}", e)
            self._scheduler = AsyncIOScheduler(
                job_defaults=self._job_defaults,
                timezone="UTC",
            )
            self._scheduler.start()
            logger.warning("Scheduler started without RedisJobStore (fallback)")

    async def shutdown(self, wait: bool = True) -> None:
        """优雅关闭调度器"""
        if self._scheduler and self._scheduler.state != STATE_STOPPED:
            self._scheduler.shutdown(wait=wait)
            logger.info("Scheduler stopped")

    def add_interval_job(
        self,
        func: Callable,
        job_id: str,
        seconds: Optional[int] = None,
        minutes: Optional[int] = None,
        hours: Optional[int] = None,
        **kwargs,
    ) -> None:
        """添加 Interval 任务"""
        if not self._scheduler:
            raise RuntimeError("Scheduler not started")

        trigger_kwargs = {}
        if seconds is not None:
            trigger_kwargs["seconds"] = seconds
        if minutes is not None:
            trigger_kwargs["minutes"] = minutes
        if hours is not None:
            trigger_kwargs["hours"] = hours

        self._scheduler.add_job(
            func,
            "interval",
            id=job_id,
            replace_existing=True,
            **trigger_kwargs,
            **self._job_defaults,
            **kwargs,
        )
        logger.debug("Registered interval job: {}", job_id)

    def add_cron_job(
        self,
        func: Callable,
        job_id: str,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
        day_of_week: Optional[str] = None,
        **kwargs,
    ) -> None:
        """添加 Cron 任务"""
        if not self._scheduler:
            raise RuntimeError("Scheduler not started")

        trigger_kwargs = {}
        if hour is not None:
            trigger_kwargs["hour"] = hour
        if minute is not None:
            trigger_kwargs["minute"] = minute
        if day_of_week is not None:
            trigger_kwargs["day_of_week"] = day_of_week

        self._scheduler.add_job(
            func,
            "cron",
            id=job_id,
            replace_existing=True,
            **trigger_kwargs,
            **self._job_defaults,
            **kwargs,
        )
        logger.debug("Registered cron job: {}", job_id)

    def remove_job(self, job_id: str) -> bool:
        """移除任务"""
        if not self._scheduler:
            return False
        try:
            self._scheduler.remove_job(job_id)
            logger.info("Removed job: {}", job_id)
            return True
        except Exception:
            return False

    def get_job(self, job_id: str) -> Optional[Any]:
        """获取任务"""
        if not self._scheduler:
            return None
        return self._scheduler.get_job(job_id)

    def list_jobs(self) -> list[dict[str, Any]]:
        """列出所有任务"""
        if not self._scheduler:
            return []
        jobs = self._scheduler.get_jobs()
        return [
            {
                "id": job.id,
                "next_run_time": job.next_run_time,
                "trigger": str(job.trigger),
            }
            for job in jobs
        ]


scheduler_service = SchedulerService()

scheduler = scheduler_service.scheduler


class PeriodicTaskRunner:
    """带幂等性检查的任务运行器（已集成到调度器中）"""

    def __init__(self, task_id: str, lock_timeout: int = 300):
        self.task_id = task_id
        self.lock_timeout = lock_timeout

    async def run(self, func: Callable, *args, **kwargs) -> bool:
        from app.worker.locks import RedisLock

        async with RedisLock.acquire_lock(
            f"task:{self.task_id}", timeout=self.lock_timeout
        ) as acquired:
            if not acquired:
                logger.info("Task {} skipped (already running)", self.task_id)
                return False

            try:
                await func(*args, **kwargs)
                logger.info("Task {} completed", self.task_id)
                return True
            except Exception as e:
                logger.error("Task {} failed: {}", self.task_id, e)
                return False


def run_with_lock(task_id: str, func: Callable, *args, **kwargs) -> bool:
    """简化的带锁任务运行"""
    runner = PeriodicTaskRunner(task_id)
    return runner.run(func, *args, **kwargs)
