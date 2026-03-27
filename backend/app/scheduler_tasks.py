from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models.models import Channel, Stream, StreamStatus, Platform
from app.services.youtube_fetcher import (
    get_channel_live_video_ids,
    get_videos_details,
    parse_youtube_stream,
)
from app.services.bilibili_fetcher import (
    get_rooms_by_uids,
    parse_bilibili_room,
    get_user_info,
)
from app.config import settings

scheduler = AsyncIOScheduler(timezone="UTC")


# ── Job 1: 发现新 YouTube 直播（高配额，每6小时）────────────────────────
async def discover_youtube_streams():
    """
    search.list = 100配额/次。只对当前没有 LIVE/UPCOMING 记录的频道执行。
    """
    if not settings.youtube_api_key:
        return

    db = SessionLocal()
    try:
        busy_channel_ids = {
            s.channel_id
            for s in db.query(Stream.channel_id)
            .filter(
                Stream.platform == Platform.YOUTUBE,
                Stream.status.in_([StreamStatus.LIVE, StreamStatus.UPCOMING]),
            )
            .all()
        }
        channels = (
            db.query(Channel)
            .filter(
                Channel.platform == Platform.YOUTUBE,
                Channel.is_active == True,
                ~Channel.id.in_(busy_channel_ids),
            )
            .all()
        )

        if not channels:
            return

        async with httpx.AsyncClient(timeout=30.0) as client:
            for ch in channels:
                try:
                    video_ids = await get_channel_live_video_ids(client, ch.channel_id)
                    if not video_ids:
                        continue
                    items = await get_videos_details(client, video_ids)
                    for item in items:
                        parsed = parse_youtube_stream(item)
                        if parsed:
                            _upsert_stream(db, ch.id, parsed, Platform.YOUTUBE)
                    db.commit()
                except Exception as e:
                    print(f"[YT Discover] {ch.name}: {e}")
                    db.rollback()

        print(f"[YT Discover] Scanned {len(channels)} idle channels")
    finally:
        db.close()


# ── Job 2: 轮询已知 YouTube 直播（1配额/50个，每分钟）──────────────────
async def update_youtube_streams():
    if not settings.youtube_api_key:
        return

    db = SessionLocal()
    try:
        active = (
            db.query(Stream)
            .filter(
                Stream.platform == Platform.YOUTUBE,
                Stream.status.in_([StreamStatus.LIVE, StreamStatus.UPCOMING]),
                Stream.video_id.isnot(None),
            )
            .all()
        )

        if not active:
            return

        vid_to_ch_id = {s.video_id: s.channel_id for s in active}
        video_ids = list(vid_to_ch_id.keys())

        async with httpx.AsyncClient(timeout=30.0) as client:
            items = await get_videos_details(client, video_ids)

        for item in items:
            parsed = parse_youtube_stream(item)
            if parsed and parsed["video_id"] in vid_to_ch_id:
                _upsert_stream(
                    db, vid_to_ch_id[parsed["video_id"]], parsed, Platform.YOUTUBE
                )

        db.commit()
        print(f"[YT Update] Refreshed {len(items)} streams")
    except Exception as e:
        print(f"[YT Update] Error: {e}")
        db.rollback()
    finally:
        db.close()


# ── Job 3: Bilibili（每2分钟，防412）────────────────────────────────────
async def update_bilibili_streams():
    db = SessionLocal()
    try:
        channels = (
            db.query(Channel)
            .filter(Channel.platform == Platform.BILIBILI, Channel.is_active == True)
            .all()
        )
        if not channels:
            return

        uid_to_ch_id = {ch.channel_id: ch.id for ch in channels}
        uids = list(uid_to_ch_id.keys())

        async with httpx.AsyncClient(timeout=30.0) as client:
            rooms_data = await get_rooms_by_uids(client, uids)

        for uid, room_data in rooms_data.items():
            if uid in uid_to_ch_id:
                parsed = parse_bilibili_room(room_data)
                _upsert_stream(db, uid_to_ch_id[uid], parsed, Platform.BILIBILI)

        db.commit()
        print(f"[Bilibili] Updated {len(rooms_data)} rooms")
    except Exception as e:
        print(f"[Bilibili] Error: {e}")
        db.rollback()
    finally:
        db.close()


# ── 通用 upsert：接收 channel.id（int），不再二次查库 ──────────────────
def _upsert_stream(db: Session, channel_id: int, parsed: dict, platform: Platform):
    stream = (
        db.query(Stream)
        .filter(Stream.channel_id == channel_id, Stream.video_id == parsed["video_id"])
        .first()
    )

    if not stream:
        stream = Stream(channel_id=channel_id, platform=platform)
        db.add(stream)

    changed = False
    for field, value in parsed.items():
        if getattr(stream, field, None) != value:
            setattr(stream, field, value)
            changed = True

    if changed:
        stream.updated_at = datetime.now(timezone.utc)
        if parsed.get("viewer_count", 0) > (stream.peak_viewers or 0):
            stream.peak_viewers = parsed["viewer_count"]


async def sync_bilibili_channels():
    """
    每日同步 B站频道的头像和名字到 Channel 表。
    调用 /x/web-interface/card，串行请求加随机延迟，避免风控。
    """
    db = SessionLocal()
    try:
        channels = (
            db.query(Channel)
            .filter(Channel.platform == Platform.BILIBILI, Channel.is_active == True)
            .all()
        )

        if not channels:
            return

        async with httpx.AsyncClient(timeout=15.0) as client:
            for ch in channels:
                info = await get_user_info(client, ch.channel_id)
                if not info:
                    continue

                changed = False
                if info.get("name") and ch.name != info["name"]:
                    ch.name = info["name"]
                    changed = True
                if info.get("avatar_url") and ch.avatar_url != info["avatar_url"]:
                    ch.avatar_url = info["avatar_url"]
                    changed = True

                if changed:
                    ch.updated_at = datetime.now(timezone.utc)

        db.commit()
        print(f"[Bilibili] Synced channel info for {len(channels)} channels")
    except Exception as e:
        print(f"[Bilibili] sync_bilibili_channels error: {e}")
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    now = datetime.now(timezone.utc)
    scheduler.add_job(
        discover_youtube_streams,
        "interval",
        hours=6,
        id="yt_discover",
        next_run_time=now,
    )
    scheduler.add_job(update_youtube_streams, "interval", seconds=60, id="yt_update")
    scheduler.add_job(
        update_bilibili_streams,
        "interval",
        minutes=2,
        id="bili_update",
        next_run_time=now,
    )
    scheduler.add_job(
        sync_bilibili_channels,
        "interval",
        hours=24,
        id="bili_sync_ch",
        next_run_time=now,
    )
    scheduler.start()
    print(
        "[Scheduler] yt_discover=6h | yt_update=60s | bili_update=2min | bili_sync_ch=24h"
    )
