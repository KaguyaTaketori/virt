from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from app.loguru_config import logger


class BaseTask(ABC):
    """后台任务基类。"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self._last_run: Optional[datetime] = None
        self._run_count: int = 0

    @property
    def last_run(self) -> Optional[datetime]:
        return self._last_run

    @property
    def run_count(self) -> int:
        return self._run_count

    @abstractmethod
    async def execute(self) -> None:
        """任务执行逻辑。子类必须实现。"""
        raise NotImplementedError

    async def run(self) -> bool:
        """运行任务，包含错误处理和统计。"""
        try:
            logger.info(" task %s start", self.task_id)
            await self.execute()
            self._last_run = datetime.now(timezone.utc)
            self._run_count += 1
            logger.info(
                " task %s completed (run_count=%d)", self.task_id, self._run_count
            )
            return True
        except Exception as e:
            logger.error(" task %s failed: %s", self.task_id, e)
            return False


class IntervalTask(BaseTask):
    """Interval 任务。"""

    def __init__(self, task_id: str, interval_seconds: int):
        super().__init__(task_id)
        self.interval_seconds = interval_seconds

    @property
    def interval(self) -> int:
        return self.interval_seconds


class CronTask(BaseTask):
    """Cron 任务。"""

    def __init__(
        self,
        task_id: str,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
        day_of_week: Optional[str] = None,
    ):
        super().__init__(task_id)
        self.hour = hour
        self.minute = minute
        self.day_of_week = day_of_week


class TaskRegistry:
    """任务注册中心。"""

    _tasks: dict[str, BaseTask] = {}

    @classmethod
    def register(cls, task: BaseTask) -> None:
        cls._tasks[task.task_id] = task

    @classmethod
    def get(cls, task_id: str) -> Optional[BaseTask]:
        return cls._tasks.get(task_id)

    @classmethod
    def get_all(cls) -> dict[str, BaseTask]:
        return cls._tasks.copy()

    @classmethod
    def list_tasks(cls) -> list[str]:
        return list(cls._tasks.keys())


def register_task(task: BaseTask) -> None:
    """装饰器：注册任务。"""
    TaskRegistry.register(task)
    return task
