# backend/app/services/bilibili_fetcher.py
"""
Bilibili Fetcher - 兼容层

已拆分到独立模块：
- bilibili_video: 视频列表获取与同步
- bilibili_profile: 用户信息获取
- bilibili_live: 直播状态获取

此文件保留用于向后兼容，新代码请直接导入上述模块。
"""

from app.services.bilibili_video import get_user_videos, sync_bilibili_channel_videos
from app.services.bilibili_profile import get_user_info, get_user_info_batch
from app.services.bilibili_live import get_rooms_by_uids, parse_bilibili_room

__all__ = [
    "get_user_videos",
    "sync_bilibili_channel_videos",
    "get_user_info",
    "get_user_info_batch",
    "get_rooms_by_uids",
    "parse_bilibili_room",
]
