"""
修复 Channel ID 迁移后的外键一致性问题

问题：Channel.id 从旧 snowflake 迁移到新 snowflake 后，
      Stream/Video 等表的 channel_id 仍指向旧 ID，导致 JOIN 失败。

解决方案：
1. 识别孤立的 Stream/Video 记录（channel_id 在新 Channel 表中不存在）
2. 删除这些孤立记录（因为无法确定对应的新 Channel）
3. 保留有效的 Stream/Video 记录

注意：如果有重要数据需要保留，需要手动匹配后更新。
"""

from __future__ import annotations

import asyncio
from sqlalchemy import select, func, text
from app.database.engine import AsyncSessionFactory
from app.database import dispose_engine
from app.models.models import (
    Stream,
    Video,
    BilibiliDynamic,
    Danmaku,
    WebSubSubscription,
    Channel,
)
from app.loguru_config import logger


async def fix_fk_consistency():
    """主修复函数"""
    async with AsyncSessionFactory() as session:
        # 1. 统计孤立记录数量
        logger.info("=== 开始外键一致性修复 ===")

        # Stream 统计
        result = await session.execute(
            text("""
            SELECT COUNT(*) FROM streams s
            LEFT JOIN channels c ON s.channel_id = c.id
            WHERE c.id IS NULL
        """)
        )
        orphan_streams = result.scalar()
        logger.info("孤立 Stream 记录: {}", orphan_streams)

        # Video 统计
        result = await session.execute(
            text("""
            SELECT COUNT(*) FROM videos v
            LEFT JOIN channels c ON v.channel_id = c.id
            WHERE c.id IS NULL
        """)
        )
        orphan_videos = result.scalar()
        logger.info("孤立 Video 记录: {}", orphan_videos)

        # BilibiliDynamic 统计
        result = await session.execute(
            text("""
            SELECT COUNT(*) FROM bilibili_dynamics bd
            LEFT JOIN channels c ON bd.channel_id = c.id
            WHERE c.id IS NULL
        """)
        )
        orphan_dynamics = result.scalar()
        logger.info("孤立 BilibiliDynamic 记录: {}", orphan_dynamics)

        # Danmaku 统计 (通过 stream)
        result = await session.execute(
            text("""
            SELECT COUNT(*) FROM danmakus d
            LEFT JOIN streams s ON d.stream_id = s.id
            WHERE s.id IS NULL
        """)
        )
        orphan_danmakus = result.scalar()
        logger.info("孤立 Danmaku 记录: {}", orphan_danmakus)

        # WebSubSubscription 统计
        result = await session.execute(
            text("""
            SELECT COUNT(*) FROM websub_subscriptions ws
            LEFT JOIN channels c ON ws.channel_id = c.id
            WHERE c.id IS NULL
        """)
        )
        orphan_subs = result.scalar()
        logger.info("孤立 WebSubSubscription 记录: {}", orphan_subs)

        # 2. 删除孤立记录
        total_deleted = 0

        if orphan_streams > 0:
            result = await session.execute(
                text("""
                DELETE FROM streams WHERE channel_id IN (
                    SELECT s.channel_id FROM streams s
                    LEFT JOIN channels c ON s.channel_id = c.id
                    WHERE c.id IS NULL
                )
            """)
            )
            await session.commit()
            deleted = result.rowcount
            total_deleted += deleted
            logger.info("已删除 {} 条孤立 Stream", deleted)

        if orphan_videos > 0:
            result = await session.execute(
                text("""
                DELETE FROM videos WHERE channel_id IN (
                    SELECT v.channel_id FROM videos v
                    LEFT JOIN channels c ON v.channel_id = c.id
                    WHERE c.id IS NULL
                )
            """)
            )
            await session.commit()
            deleted = result.rowcount
            total_deleted += deleted
            logger.info("已删除 {} 条孤立 Video", deleted)

        if orphan_dynamics > 0:
            result = await session.execute(
                text("""
                DELETE FROM bilibili_dynamics WHERE channel_id IN (
                    SELECT bd.channel_id FROM bilibili_dynamics bd
                    LEFT JOIN channels c ON bd.channel_id = c.id
                    WHERE c.id IS NULL
                )
            """)
            )
            await session.commit()
            deleted = result.rowcount
            total_deleted += deleted
            logger.info("已删除 {} 条孤立 BilibiliDynamic", deleted)

        if orphan_danmakus > 0:
            result = await session.execute(
                text("""
                DELETE FROM danmakus WHERE stream_id IN (
                    SELECT d.stream_id FROM danmakus d
                    LEFT JOIN streams s ON d.stream_id = s.id
                    WHERE s.id IS NULL
                )
            """)
            )
            await session.commit()
            deleted = result.rowcount
            total_deleted += deleted
            logger.info("已删除 {} 条孤立 Danmaku", deleted)

        if orphan_subs > 0:
            result = await session.execute(
                text("""
                DELETE FROM websub_subscriptions WHERE channel_id IN (
                    SELECT ws.channel_id FROM websub_subscriptions ws
                    LEFT JOIN channels c ON ws.channel_id = c.id
                    WHERE c.id IS NULL
                )
            """)
            )
            await session.commit()
            deleted = result.rowcount
            total_deleted += deleted
            logger.info("已删除 {} 条孤立 WebSubSubscription", deleted)

        # 3. 验证修复结果
        logger.info("=== 验证修复结果 ===")

        result = await session.execute(text("SELECT COUNT(*) FROM streams"))
        total_streams = result.scalar()
        logger.info("Stream 总数: {}", total_streams)

        result = await session.execute(text("SELECT COUNT(*) FROM videos"))
        total_videos = result.scalar()
        logger.info("Video 总数: {}", total_videos)

        # 检查是否还有孤立记录
        result = await session.execute(
            text("""
            SELECT COUNT(*) FROM streams s
            LEFT JOIN channels c ON s.channel_id = c.id
            WHERE c.id IS NULL
        """)
        )
        remaining = result.scalar()
        logger.info("剩余孤立 Stream: {}", remaining)

        return total_deleted


async def main():
    logger.info("=" * 60)
    logger.info("Channel ID 迁移后外键一致性修复")
    logger.info("=" * 60)

    try:
        deleted = await fix_fk_consistency()

        logger.info("=" * 60)
        logger.info("修复完成！共删除 {} 条孤立记录", deleted)
        logger.info("=" * 60)

    except Exception as e:
        logger.error("修复失败: {}", e)
        raise
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
