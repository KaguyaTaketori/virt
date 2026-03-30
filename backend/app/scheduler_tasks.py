# backend/app/scheduler_tasks.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.models import Channel, Stream, StreamStatus, Platform
from app.services.youtube_fetcher import (
    get_channel_live_video_ids,
    get_channel_upcoming_video_ids,
    get_videos_details,
    parse_youtube_stream,
)
from app.services.bilibili_fetcher import (
    get_rooms_by_uids,
    parse_bilibili_room,
    get_user_info,
)
from app.services.quota_guard import can_spend, spend, status as quota_status
from app.services.youtube_channel import get_channel_details
from app.config import settings

scheduler = AsyncIOScheduler(timezone="UTC")


# ── YouTube ───────────────────────────────────────────────────────────────────


async def discover_youtube_streams():
    """
    用 search.list（100配额/次）发现新直播。
    只扫当前没有 LIVE/UPCOMING 记录的频道，且受配额守卫严格限制。
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

        q = quota_status()
        print(f"[YT Discover] 待扫描 {len(channels)} 频道 | 配额剩余 {q['remaining']}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            for ch in channels:
                # 每次 search.list = 100 配额，提前检查
                if not can_spend("search.list", 1):
                    print(f"[YT Discover] 配额不足，提前终止（已处理到 {ch.name}）")
                    break

                try:
                    # 查 live
                    live_ids = await get_channel_live_video_ids(client, ch.channel_id)
                    spend("search.list", 1)

                    # 查 upcoming（再消耗 100）
                    upcoming_ids = []
                    if can_spend("search.list", 1):
                        upcoming_ids = await get_channel_upcoming_video_ids(
                            client, ch.channel_id
                        )
                        spend("search.list", 1)

                    all_ids = list(set(live_ids + upcoming_ids))
                    if not all_ids:
                        continue

                    # videos.list = 1 配额（50条以内）
                    if can_spend("videos.list", 1):
                        items = await get_videos_details(client, all_ids)
                        spend("videos.list", 1)
                        for item in items:
                            parsed = parse_youtube_stream(item)
                            if parsed:
                                _upsert_stream(db, ch.id, parsed, Platform.YOUTUBE)
                        db.commit()

                except Exception as e:
                    print(f"[YT Discover] {ch.name}: {e}")
                    db.rollback()

        print(f"[YT Discover] 完成 | 配额剩余 {quota_status()['remaining']}")
    finally:
        db.close()


async def update_youtube_streams():
    """
    用 videos.list（1配额/次）刷新已知活跃流的状态。
    配额消耗极低，只要有剩余就跑。
    """
    if not settings.youtube_api_key:
        return

    # update 是高优先级，只要还有配额就执行（不设 discover_reserve 限制）
    if not can_spend("videos.list", 1):
        print("[YT Update] 配额耗尽，跳过")
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
            # 50 个一批，每批消耗 1 配额
            for i in range(0, len(video_ids), 50):
                chunk = video_ids[i : i + 50]
                if not can_spend("videos.list", 1):
                    print("[YT Update] 配额耗尽，停止当前批次")
                    break
                items = await get_videos_details(client, chunk)
                spend("videos.list", 1)
                for item in items:
                    parsed = parse_youtube_stream(item)
                    if parsed and parsed["video_id"] in vid_to_ch_id:
                        _upsert_stream(
                            db,
                            vid_to_ch_id[parsed["video_id"]],
                            parsed,
                            Platform.YOUTUBE,
                        )

        db.commit()
        print(
            f"[YT Update] 刷新 {len(active)} 条 | 配额剩余 {quota_status()['remaining']}"
        )
    except Exception as e:
        print(f"[YT Update] Error: {e}")
        db.rollback()
    finally:
        db.close()


# ── Bilibili ──────────────────────────────────────────────────────────────────


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
        print(f"[Bilibili] 更新 {len(rooms_data)} 个房间")
    except Exception as e:
        print(f"[Bilibili] Error: {e}")
        db.rollback()
    finally:
        db.close()


async def sync_bilibili_channels():
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
        print(f"[Bilibili] 同步 {len(channels)} 个频道信息")
    except Exception as e:
        print(f"[Bilibili] sync_bilibili_channels error: {e}")
        db.rollback()
    finally:
        db.close()


# ── 共用 upsert ───────────────────────────────────────────────────────────────


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


# ── 频道详情刷新 ─────────────────────────────────────────────────────────────


async def refresh_channel_details():
    """每天执行，刷新所有频道的 banner/描述/链接"""
    if not settings.youtube_api_key:
        return

    db = SessionLocal()
    try:
        channels = (
            db.query(Channel)
            .filter(
                Channel.platform == Platform.YOUTUBE,
                Channel.is_active == True,
            )
            .all()
        )

        if not channels:
            return

        print(f"[Channel Refresh] 开始刷新 {len(channels)} 个 YouTube 频道")

        async with httpx.AsyncClient(timeout=30.0) as client:
            for ch in channels:
                try:
                    details = await get_channel_details(ch.channel_id)
                    if details:
                        changed = False
                        if (
                            details.get("banner_url")
                            and ch.banner_url != details["banner_url"]
                        ):
                            ch.banner_url = details["banner_url"]
                            changed = True
                        if (
                            details.get("description")
                            and ch.description != details["description"]
                        ):
                            ch.description = details["description"]
                            changed = True
                        if (
                            details.get("twitter_url")
                            and ch.twitter_url != details["twitter_url"]
                        ):
                            ch.twitter_url = details["twitter_url"]
                            changed = True
                        if (
                            details.get("youtube_url")
                            and ch.youtube_url != details["youtube_url"]
                        ):
                            ch.youtube_url = details["youtube_url"]
                            changed = True
                        if changed:
                            ch.updated_at = datetime.now(timezone.utc)
                except Exception as e:
                    print(f"[Channel Refresh] {ch.name}: {e}")

        db.commit()
        print(f"[Channel Refresh] 完成")
    except Exception as e:
        print(f"[Channel Refresh] Error: {e}")
        db.rollback()
    finally:
        db.close()


# ── 调度器启动 ────────────────────────────────────────────────────────────────


def start_scheduler():
    now = datetime.now(timezone.utc)
    scheduler.add_job(
        discover_youtube_streams,
        "interval",
        hours=6,
        id="yt_discover",
        next_run_time=now,
    )
    scheduler.add_job(
        update_youtube_streams,
        "interval",
        seconds=60,
        id="yt_update",
    )
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
    scheduler.add_job(
        refresh_channel_details,
        "interval",
        hours=24,
        id="channel_refresh",
        next_run_time=now,
    )
    scheduler.start()
    print(
        "[Scheduler] yt_discover=6h | yt_update=60s | bili_update=2min | bili_sync_ch=24h | channel_refresh=24h"
    )
