"""
重建 Stream 数据脚本
运行后会为所有活跃的 YouTube 频道创建 Stream 记录
"""

import asyncio
from app.config import settings
from app.services.api_key_manager import api_key_manager
from app.worker.tasks.youtube import sync_youtube_videos_full

api_key_manager.initialize(settings.youtube_api_keys_list)

if __name__ == "__main__":
    asyncio.run(sync_youtube_videos_full(limit=70))
