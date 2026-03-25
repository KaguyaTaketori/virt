from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models.models import Channel, Stream, StreamStatus, Platform
from app.services.youtube_fetcher import (
    get_channel_live_video_ids, get_videos_details, parse_youtube_stream
)
from app.services.bilibili_fetcher import (
    get_rooms_by_uids, parse_bilibili_room
)

scheduler = AsyncIOScheduler(timezone="UTC")


async def update_youtube_streams():
    db = SessionLocal()
    try:
        channels = (
            db.query(Channel)
            .filter(Channel.platform == Platform.YOUTUBE, Channel.is_active == True)
            .all()
        )
        
        async with httpx.AsyncClient() as client:
            # Step 1: 收集所有已知的 live/upcoming videoId
            known_live_ids = [
                s.video_id for s in
                db.query(Stream).filter(
                    Stream.platform == Platform.YOUTUBE,
                    Stream.status.in_([StreamStatus.LIVE, StreamStatus.UPCOMING])
                ).all()
                if s.video_id
            ]
            
            # Step 2: 批量查询已知视频的最新状态（低配额消耗）
            items = await get_videos_details(client, known_live_ids)
            
            for item in items:
                parsed = parse_youtube_stream(item)
                if not parsed:
                    continue
                _upsert_stream(db, item["snippet"]["channelId"], parsed, Platform.YOUTUBE)
        
        db.commit()
        print(f"[YouTube] Updated {len(items)} streams")
    except Exception as e:
        print(f"[YouTube] Error: {e}")
        db.rollback()
    finally:
        db.close()


async def update_bilibili_streams():
    db = SessionLocal()
    try:
        channels = (
            db.query(Channel)
            .filter(Channel.platform == Platform.BILIBILI, Channel.is_active == True)
            .all()
        )
        uids = [ch.channel_id for ch in channels]
        
        async with httpx.AsyncClient() as client:
            rooms_data = await get_rooms_by_uids(client, uids)
        
        for uid, room_data in rooms_data.items():
            parsed = parse_bilibili_room(room_data)
            _upsert_stream(db, uid, parsed, Platform.BILIBILI)
        
        db.commit()
        print(f"[Bilibili] Updated {len(rooms_data)} rooms")
    except Exception as e:
        print(f"[Bilibili] Error: {e}")
        db.rollback()
    finally:
        db.close()


def _upsert_stream(db: Session, platform_channel_id: str, parsed: dict, platform: Platform):
    """差量更新：只有字段变化时才写入 DB"""
    channel = db.query(Channel).filter(Channel.channel_id == platform_channel_id).first()
    if not channel:
        return
    
    stream = (
        db.query(Stream)
        .filter(Stream.channel_id == channel.id, Stream.video_id == parsed["video_id"])
        .first()
    )
    
    if not stream:
        stream = Stream(channel_id=channel.id, platform=platform)
        db.add(stream)
    
    # 差量检测：只有值变化才更新
    changed = False
    for field, value in parsed.items():
        if getattr(stream, field, None) != value:
            setattr(stream, field, value)
            changed = True
    
    if changed:
        stream.updated_at = datetime.now(timezone.utc)
        # 记录峰值观看
        if parsed.get("viewer_count", 0) > (stream.peak_viewers or 0):
            stream.peak_viewers = parsed["viewer_count"]


def start_scheduler():
    # YouTube：已知流每 1 分钟更新观看数；发现新流每 5 分钟扫描一次
    scheduler.add_job(update_youtube_streams, "interval", minutes=1,  id="yt_update")
    scheduler.add_job(update_bilibili_streams, "interval", minutes=1,  id="bili_update")
    scheduler.start()
    print("[Scheduler] Started")