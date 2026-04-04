import json
from app.loguru_config import logger
from typing import List, Optional
from pathlib import Path

from yt_chat_downloader import YouTubeChatDownloader
from app.config import settings
from app.models.models import Danmaku
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


def get_danmaku_file_path(video_id: str) -> Path:
    """获取弹幕JSON文件路径"""
    storage_dir = Path(settings.danmaku_storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir / f"youtube_{video_id}.json"


def download_chat(video_id: str, chat_type: str = "live") -> Optional[List[dict]]:
    """下载YouTube弹幕到JSON文件"""
    try:
        downloader = YouTubeChatDownloader()
        messages = downloader.download_chat(
            video_url=video_id,
            chat_type=chat_type,
            quiet=True,
        )

        if messages:
            file_path = get_danmaku_file_path(video_id)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
            return messages
        return None
    except Exception as e:
        logger.error("Failed to download chat for {}: {}", video_id, e)
        return None


def get_chat_from_file(video_id: str) -> List[dict]:
    """从本地JSON文件读取弹幕"""
    file_path = get_danmaku_file_path(video_id)
    if not file_path.exists():
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to read chat file for {}: {}", video_id, e)
        return []


async def get_chat_from_db(db: AsyncSession, stream_id: int) -> List[dict]:
    """从数据库读取弹幕"""
    result = await db.execute(select(Danmaku).where(Danmaku.stream_id == stream_id))
    danmaku = result.scalar_one_or_none()
    if not danmaku:
        return []

    try:
        return json.loads(danmaku.messages)
    except json.JSONDecodeError:
        return []


async def save_to_db(
    db: AsyncSession, stream_id: int, video_id: str, messages: List[dict]
) -> Danmaku:
    """保存弹幕到数据库"""
    result = await db.execute(select(Danmaku).where(Danmaku.stream_id == stream_id))
    existing = result.scalar_one_or_none()

    json_messages = json.dumps(messages, ensure_ascii=False)

    if existing:
        existing.messages = json_messages
        existing.downloaded_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        danmaku = Danmaku(
            stream_id=stream_id,
            video_id=video_id,
            messages=json_messages,
            source="youtube",
        )
        db.add(danmaku)
        await db.commit()
        await db.refresh(danmaku)
        return danmaku
