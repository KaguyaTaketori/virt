from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from app.database import SessionLocal
from app.models.models import Stream, StreamStatus, Channel


scheduler = AsyncIOScheduler()


async def fetch_youtube_live_status():
    """
    模拟从 YouTube API 获取直播状态
    实际项目中需要调用 YouTube Data API v3
    """
    db = SessionLocal()
    try:
        channels = db.query(Channel).filter(Channel.platform == "youtube").all()
        for channel in channels:
            print(f"[Scheduler] Checking YouTube channel: {channel.channel_id}")
            # TODO: 实际实现需要调用 YouTube API
            # 伪代码示例:
            # response = await youtube_api.get_live_streams(channel.channel_id)
            # update_stream_status(channel.id, response)
            pass
    finally:
        db.close()


async def fetch_bilibili_live_status():
    """
    模拟从 Bilibili API 获取直播状态
    实际项目中需要调用 Bilibili API
    """
    db = SessionLocal()
    try:
        channels = db.query(Channel).filter(Channel.platform == "bilibili").all()
        for channel in channels:
            print(f"[Scheduler] Checking Bilibili room: {channel.channel_id}")
            # TODO: 实际实现需要调用 Bilibili API
            # 伪代码示例:
            # response = await bilibili_api.get_room_info(channel.channel_id)
            # update_stream_status(channel.id, response)
            pass
    finally:
        db.close()


def update_stream_from_api(channel_id: int, api_response: dict):
    """
    根据 API 响应更新数据库中的直播状态
    """
    db = SessionLocal()
    try:
        stream = db.query(Stream).filter(Stream.channel_id == channel_id).first()
        
        if not stream:
            stream = Stream(channel_id=channel_id)
            db.add(stream)
        
        stream.status = StreamStatus.LIVE if api_response.get("is_live") else StreamStatus.OFFLINE
        stream.title = api_response.get("title")
        stream.viewer_count = api_response.get("viewer_count", 0)
        stream.video_id = api_response.get("video_id")
        stream.thumbnail_url = api_response.get("thumbnail")
        stream.updated_at = datetime.utcnow()
        
        if api_response.get("is_live"):
            stream.started_at = api_response.get("started_at")
        
        db.commit()
    finally:
        db.close()


def start_scheduler():
    """
    启动定时任务调度器
    每分钟执行一次更新任务
    """
    scheduler.add_job(fetch_youtube_live_status, 'interval', minutes=1, id='youtube_fetch')
    scheduler.add_job(fetch_bilibili_live_status, 'interval', minutes=1, id='bilibili_fetch')
    scheduler.start()
    print("[Scheduler] Background task scheduler started")