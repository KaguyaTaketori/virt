from typing import Optional
import json
from datetime import datetime, timezone

from app.loguru_config import logger
from app.services.redis_client import RedisClient

_INCREMENTAL_PREFIX = "youtube:sync:incremental:"
_FULL_PREFIX = "youtube:sync:full:"
_FULL_ALL_COMPLETED = "youtube:sync:full:all_completed"


async def _get_redis():
    try:
        return await RedisClient.get_client()
    except Exception as e:
        logger.error("Redis 连接失败: {}", e)
        return None


async def get_incremental_state(channel_id: int) -> Optional[dict]:
    """获取频道的增量同步状态"""
    redis = await _get_redis()
    if not redis:
        return None

    try:
        data = await redis.get(f"{_INCREMENTAL_PREFIX}{channel_id}")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.error("获取增量同步状态失败 channel_id={}: {}", channel_id, e)
    return None


async def set_incremental_state(channel_id: int, video_count: int) -> bool:
    """设置频道的增量同步状态"""
    redis = await _get_redis()
    if not redis:
        return False

    try:
        state = {
            "video_count": video_count,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
        await redis.set(f"{_INCREMENTAL_PREFIX}{channel_id}", json.dumps(state))
        return True
    except Exception as e:
        logger.error("设置增量同步状态失败 channel_id={}: {}", channel_id, e)
        return False


async def reset_incremental_state(channel_id: int) -> bool:
    """重置频道的增量同步状态"""
    redis = await _get_redis()
    if not redis:
        return False

    try:
        await redis.delete(f"{_INCREMENTAL_PREFIX}{channel_id}")
        return True
    except Exception as e:
        logger.error("重置增量同步状态失败 channel_id={}: {}", channel_id, e)
        return False


async def get_full_state(channel_id: int) -> Optional[dict]:
    """获取频道的全量同步状态"""
    redis = await _get_redis()
    if not redis:
        return None

    try:
        data = await redis.get(f"{_FULL_PREFIX}{channel_id}")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.error("获取全量同步状态失败 channel_id={}: {}", channel_id, e)
    return None


async def set_full_completed(channel_id: int, playlist_total: int) -> bool:
    """标记频道全量同步完成"""
    redis = await _get_redis()
    if not redis:
        return False

    try:
        state = {
            "completed": True,
            "playlist_total": playlist_total,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
        await redis.set(f"{_FULL_PREFIX}{channel_id}", json.dumps(state))
        return True
    except Exception as e:
        logger.error("设置全量同步状态失败 channel_id={}: {}", channel_id, e)
        return False


async def reset_full_state(channel_id: int) -> bool:
    """重置频道的全量同步状态"""
    redis = await _get_redis()
    if not redis:
        return False

    try:
        await redis.delete(f"{_FULL_PREFIX}{channel_id}")
        return True
    except Exception as e:
        logger.error("重置全量同步状态失败 channel_id={}: {}", channel_id, e)
        return False


async def is_all_full_completed() -> bool:
    """检查是否所有频道都完成了全量同步"""
    redis = await _get_redis()
    if not redis:
        return False

    try:
        data = await redis.get(_FULL_ALL_COMPLETED)
        return data == "true"
    except Exception as e:
        logger.error("检查全量完成状态失败: {}", e)
        return False


async def set_all_full_completed(completed: bool) -> bool:
    """设置全量同步全部完成标记"""
    redis = await _get_redis()
    if not redis:
        return False

    try:
        await redis.set(_FULL_ALL_COMPLETED, "true" if completed else "false")
        return True
    except Exception as e:
        logger.error("设置全量完成标记失败: {}", e)
        return False


async def clear_all_sync_states() -> int:
    """清除所有同步状态"""
    redis = await _get_redis()
    if not redis:
        return 0

    try:
        deleted_count = 0
        cursor = 0

        patterns = [f"{_INCREMENTAL_PREFIX}*", f"{_FULL_PREFIX}*", _FULL_ALL_COMPLETED]
        for pattern in patterns:
            while True:
                cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    deleted_count += await redis.delete(*keys)
                if cursor == 0:
                    break

        logger.info("已清除 {} 个同步状态", deleted_count)
        return deleted_count
    except Exception as e:
        logger.error("清除所有同步状态失败: {}", e)
        return 0
