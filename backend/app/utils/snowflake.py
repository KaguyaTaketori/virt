"""Snowflake ID 生成器 - 64位ID

结构 (高位到低位):
- 1位: 符号位 (始终为0, 保证正数)
- 41位: 时间戳 (毫秒, 相对于 SNOWFLAKE_EPOCH)
- 5位: 数据中心ID (0-31)
- 5位: 机器ID (0-31)
- 12位: 序列号 (0-4095)

可使用到 2065 年 (基于 2024-01-01 Epoch)
"""

import threading
import time
from dataclasses import dataclass, field

SNOWFLAKE_EPOCH = 1704067200000

MAX_worker_ID = 31
MAX_DATACENTER_ID = 31
MAX_SEQUENCE = 4095


class SnowflakeIdError(Exception):
    pass


@dataclass
class SnowflakeGenerator:
    """线程安全的 Snowflake ID 生成器"""

    worker_id: int
    datacenter_id: int
    sequence: int = field(default=0, init=False)
    last_timestamp: int = field(default=0, init=False)
    lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def __post_init__(self):
        if not 0 <= self.worker_id <= MAX_worker_ID:
            raise SnowflakeIdError(
                f"worker_id 必须在 0-31 之间, 当前值: {self.worker_id}"
            )
        if not 0 <= self.datacenter_id <= MAX_DATACENTER_ID:
            raise SnowflakeIdError(
                f"datacenter_id 必须在 0-31 之间, 当前值: {self.datacenter_id}"
            )

    def generate_id(self) -> int:
        """生成唯一的 Snowflake ID"""
        with self.lock:
            current_timestamp = self._current_timestamp()

            if current_timestamp < self.last_timestamp:
                raise SnowflakeIdError(
                    f"时钟回拨检测到: 当前时间戳 {current_timestamp} "
                    f"小于上次时间戳 {self.last_timestamp}"
                )

            if current_timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & MAX_SEQUENCE
                if self.sequence == 0:
                    current_timestamp = self._wait_next_timestamp()
            else:
                self.sequence = 0

            self.last_timestamp = current_timestamp

            snowflake_id = (
                ((current_timestamp - SNOWFLAKE_EPOCH) << 22)
                | (self.datacenter_id << 17)
                | (self.worker_id << 12)
                | self.sequence
            )

            return snowflake_id

    def _current_timestamp(self) -> int:
        """获取当前时间戳 (毫秒)"""
        return int(time.time() * 1000)

    def _wait_next_timestamp(self) -> int:
        """等待下一毫秒并返回时间戳"""
        timestamp = self._current_timestamp()
        while timestamp <= self.last_timestamp:
            time.sleep(0.001)
            timestamp = self._current_timestamp()
        return timestamp


_instance = None


def get_snowflake_generator() -> SnowflakeGenerator:
    """获取全局 Snowflake 生成器实例，延迟导入避免循环依赖"""
    global _instance
    if _instance is None:
        from app.config import settings

        if settings.snowflake_worker_id < 0 or settings.snowflake_worker_id > 31:
            raise SnowflakeIdError(
                f"SNOWFLAKE_WORKER_ID 必须 在 0-31 之间, 当前配置: {settings.snowflake_worker_id}"
            )

        if (
            settings.snowflake_datacenter_id < 0
            or settings.snowflake_datacenter_id > 31
        ):
            raise SnowflakeIdError(
                f"SNOWFLAKE_DATACENTER_ID 必须 在 0-31 之间, 当前配置: {settings.snowflake_datacenter_id}"
            )

        _instance = SnowflakeGenerator(
            worker_id=settings.snowflake_worker_id,
            datacenter_id=settings.snowflake_datacenter_id,
        )
    return _instance


def generate_channel_id() -> int:
    """生成 Channel 专用的 Snowflake ID"""
    return get_snowflake_generator().generate_id()


snowflake_gen = get_snowflake_generator()
