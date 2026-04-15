"""
Snowflake ID 生成器 - 64位ID

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

# 常量定义
SNOWFLAKE_EPOCH = 1704067200000  # 2024-01-01 00:00:00 UTC
MAX_worker_ID = 31
MAX_DATACENTER_ID = 31
MAX_SEQUENCE = 4095

class SnowflakeIdError(Exception):
    """Snowflake 相关异常"""
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
        # 验证 worker_id
        if not (0 <= self.worker_id <= MAX_worker_ID):
            raise SnowflakeIdError(f'worker_id 必须在 0-31 之间, 当前值: {self.worker_id}')
        
        # 验证 datacenter_id
        if not (0 <= self.datacenter_id <= MAX_DATACENTER_ID):
            raise SnowflakeIdError(f'datacenter_id 必须在 0-31 之间, 当前值: {self.datacenter_id}')

    def generate_id(self) -> int:
        """生成一个新的 Snowflake ID"""
        with self.lock:
            current_timestamp = self._current_timestamp()

            # 时钟回拨检测
            if current_timestamp < self.last_timestamp:
                raise SnowflakeIdError(
                    f'时钟回拨检测到: 当前时间戳 {current_timestamp} 小于上次时间戳 {self.last_timestamp}'
                )

            # 同一毫秒内
            if current_timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & MAX_SEQUENCE
                if self.sequence == 0:
                    # 序列号溢出，等待下一毫秒
                    current_timestamp = self._wait_next_timestamp()
            else:
                # 不同毫秒，序列号重置
                self.sequence = 0

            self.last_timestamp = current_timestamp

            # 位运算拼接 ID
            snowflake_id = (
                ((current_timestamp - SNOWFLAKE_EPOCH) << 22) |
                (self.datacenter_id << 17) |
                (self.worker_id << 12) |
                self.sequence
            )
            return snowflake_id

    def _current_timestamp(self) -> int:
        """获取当前毫秒级时间戳"""
        return int(time.time() * 1000)

    def _wait_next_timestamp(self) -> int:
        """自旋等待直到下一毫秒"""
        timestamp = self._current_timestamp()
        while timestamp <= self.last_timestamp:
            time.sleep(0.001)
            timestamp = self._current_timestamp()
        return timestamp

# 单例实例存储
_instance = None

def get_snowflake_generator() -> SnowflakeGenerator:
    """获取 Snowflake 生成器单例"""
    global _instance
    if _instance is None:
        from app.config import settings
        
        # 从配置中验证并读取
        if settings.snowflake_worker_id < 0 or settings.snowflake_worker_id > 31:
            raise SnowflakeIdError(f'SNOWFLAKE_WORKER_ID 必须 在 0-31 之间, 当前配置: {settings.snowflake_worker_id}')
        
        if settings.snowflake_datacenter_id < 0 or settings.snowflake_datacenter_id > 31:
            raise SnowflakeIdError(f'SNOWFLAKE_DATACENTER_ID 必须 在 0-31 之间, 当前配置: {settings.snowflake_datacenter_id}')
            
        _instance = SnowflakeGenerator(
            worker_id=settings.snowflake_worker_id,
            datacenter_id=settings.snowflake_datacenter_id
        )
    return _instance

def generate_channel_id() -> int:
    return get_snowflake_generator().generate_id()

snowflake_gen = get_snowflake_generator()