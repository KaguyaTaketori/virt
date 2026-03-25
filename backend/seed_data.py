from app.database import SessionLocal, engine, Base
from app.models.models import Channel, Stream, Platform, StreamStatus
from datetime import datetime


from datetime import datetime, timezone


def seed_data():
    Base.metadata.create_all(bind=engine)
    
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    
    channels_data = [
        {"platform": Platform.YOUTUBE, "channel_id": "UC1DCed4u1q4yVJ5vL0K4Cgw", "name": "Hoshimachi Suisei", "avatar_url": "https://yt3.googleusercontent.com/ytc/AKedOLRvKqBdSJQjFG2LEJbNVk1j1nJ3Z4P8Z9K1T6oT1g=s176-c-k-c0x00ffffff-no-rj"},
        {"platform": Platform.YOUTUBE, "channel_id": "UCvzGlP9oQwU--IlCj3D9_mA", "name": "Mori Calliope", "avatar_url": "https://yt3.googleusercontent.com/ytc/AKedOLTu0V9kV3V5qT9qZ9qZ9qZ9qZ9qZ9qZ9qZ9qZ9qZ9q=s176-c-k-c0x00ffffff-no-rj"},
        {"platform": Platform.BILIBILI, "channel_id": "23055458", "name": "Kizuna AI", "avatar_url": "https://i0.hdslb.com/bfs/face/3c5e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3.jpg"},
        {"platform": Platform.BILIBILI, "channel_id": "211267838", "name": "Kurokishi White", "avatar_url": "https://i0.hdslb.com/bfs/face/1234567890abcdef1234567890abcdef.jpg"},
    ]
    
    existing = db.query(Channel).count()
    if existing > 0:
        print(f"Database already has {existing} channels. Skipping seed.")
        return
    
    channels = []
    for ch in channels_data:
        channel = Channel(**ch)
        db.add(channel)
        channels.append(channel)
    
    db.commit()
    
    streams_data = [
        {
            "channel_id": channels[0].id,
            "platform": Platform.YOUTUBE,
            "video_id": "abc123xyz",
            "title": "【歌枠】になりました！🌟",
            "thumbnail_url": "https://i.ytimg.com/vi/abc123xyz/maxresdefault.jpg",
            "viewer_count": 15234,
            "status": StreamStatus.LIVE,
            "started_at": now
        },
        {
            "channel_id": channels[1].id,
            "platform": Platform.YOUTUBE,
            "video_id": "def456uvw",
            "title": "REAPER MC Stream! 🎤",
            "thumbnail_url": "https://i.ytimg.com/vi/def456uvw/maxresdefault.jpg",
            "viewer_count": 8921,
            "status": StreamStatus.LIVE,
            "started_at": now
        },
        {
            "channel_id": channels[2].id,
            "platform": Platform.BILIBILI,
            "video_id": "23055458",
            "title": "A.I.Channel #100 🎉",
            "thumbnail_url": "https://i0.hdslb.com/bfs/live/new_cover/23055458.jpg",
            "viewer_count": 45678,
            "status": StreamStatus.LIVE,
            "started_at": now
        },
        {
            "channel_id": channels[3].id,
            "platform": Platform.BILIBILI,
            "video_id": "211267838",
            "title": "白 Cinderella",
            "thumbnail_url": "https://i0.hdslb.com/bfs/live/new_cover/211267838.jpg",
            "viewer_count": 22345,
            "status": StreamStatus.LIVE,
            "started_at": now
        },
    ]
    
    for st in streams_data:
        stream = Stream(**st)
        db.add(stream)
    
    db.commit()
    print(f"Seeded {len(channels)} channels and {len(streams_data)} streams!")
    db.close()


if __name__ == "__main__":
    seed_data()