# backend/app/scheduler_tasks.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx
from app.loguru_config import logger
import os
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.models import Channel, Stream, StreamStatus, Platform
from app.services.youtube_fetcher import (
    get_videos_details,
    parse_youtube_stream,
)
from app.services.bilibili_fetcher import (
    get_rooms_by_uids,
    parse_bilibili_room,
    get_user_info,
    sync_bilibili_channel_videos,
)
from app.services.quota_guard import can_spend, spend, status as quota_status
from app.services.youtube_channel import get_channel_details
from app.config import settings
from app.services.youtube_websub import subscribe_all_active_channels
from app.services.youtube_sync import sync_channel_videos
from app.database_async import AsyncSessionFactory

scheduler = AsyncIOScheduler(timezone="UTC")


# ── YouTube ───────────────────────────────────────────────────────────────────
async def _daily_backfill_sync():
    """
    每日兜底对账：用 PlaylistItems(UUxxx) 增量同步每个频道的最新50条。
    配额消耗极低：每频道约 2 配额，100频道 ≈ 200 配额/天。
    补漏 WebSub 可能遗漏的视频。
    """
    api_key = settings.youtube_api_key
    if not api_key:
        return

    async with AsyncSessionFactory() as session:
        from sqlalchemy import select
        from app.models.models import Channel, Platform

        result = await session.execute(
            select(Channel).where(
                Channel.platform == Platform.YOUTUBE,
                Channel.is_active == True,
            )
        )
        channels = result.scalars().all()

    for ch in channels:
        async with AsyncSessionFactory() as session:
            ch_obj = await session.get(Channel, ch.id)
            if ch_obj:
                await sync_channel_videos(session, ch_obj, api_key, full_refresh=False)


async def _renew_websub():
    """每 8 天续订所有频道的 WebSub 订阅，避免 10 天后过期失效。"""
    callback_url = os.getenv(
        "WEBSUB_CALLBACK_URL", "https://your-domain.com/api/websub/youtube"
    )
    await subscribe_all_active_channels(callback_url)


async def discover_youtube_streams():
    """
    Search-based stream discovery 已禁用。

    现在的策略：
    - 更新已知活跃流：用 videos.list（update_youtube_streams）
    - 查询“正在直播”：在 API 层按需用 youtube_sync 增量拉取
    """
    return


async def update_youtube_streams():
    """
    用 videos.list（1配额/次）刷新已知活跃流的状态。
    配额消耗极低，只要有剩余就跑。
    """
    if not settings.youtube_api_key:
        return

    # update 是高优先级，只要还有配额就执行（不设 discover_reserve 限制）
    if not can_spend("videos.list", 1):
        logger.info("配额耗尽，跳过")
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
                    logger.info("配额耗尽，停止当前批次")
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
        logger.info(
            "刷新 {} 条 | 配额剩余 {}", len(active), quota_status()["remaining"]
        )
    except Exception as e:
        logger.error("Error: {}", e)
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
        logger.info("更新 {} 个房间", len(rooms_data))
    except Exception as e:
        logger.error("Error: {}", e)
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

        async with httpx.AsyncClient(timeout=30.0) as client:
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

                total_synced = await sync_bilibili_channel_videos(
                    db, ch.id, ch.channel_id
                )
                if total_synced > 0:
                    logger.info("{}: 同步了 {} 个视频", ch.name, total_synced)

        db.commit()
        logger.info("同步 {} 个频道信息", len(channels))
    except Exception as e:
        logger.error("sync_bilibili_channels error: {}", e)
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

        logger.info("开始刷新 {} 个 YouTube 频道", len(channels))

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
                    logger.warning("{}: {}", ch.name, e)

        db.commit()
        logger.info("完成")
    except Exception as e:
        logger.error("Error: {}", e)
        db.rollback()
    finally:
        db.close()


# ── 调度器启动 ────────────────────────────────────────────────────────────────


def start_scheduler():
    # 允许重复调用（例如 uvicorn --reload 会触发 lifespan），避免重复 start/add_job。
    if getattr(scheduler, "running", False):
        return

    now = datetime.now(timezone.utc)
    scheduler.add_job(
        update_youtube_streams,
        "interval",
        minutes=5,
        id="yt_update",
        replace_existing=True,
    )
    scheduler.add_job(
        update_bilibili_streams,
        "interval",
        minutes=2,
        id="bili_update",
        next_run_time=now,
        replace_existing=True,
    )
    scheduler.add_job(
        sync_bilibili_channels,
        "interval",
        hours=24,
        id="bili_sync_ch",
        next_run_time=now,
        replace_existing=True,
    )
    scheduler.add_job(
        refresh_channel_details,
        "interval",
        hours=24,
        id="channel_refresh",
        next_run_time=now,
        replace_existing=True,
    )
    logger.info("yt_discover=已禁用 | yt_update=5min | bili_update=2min")

    scheduler.add_job(
        _daily_backfill_sync,
        "cron",
        hour=4,
        minute=0,  # UTC 04:00
        id="daily_backfill",
        replace_existing=True,
    )
    scheduler.add_job(
        _renew_websub,
        "interval",
        days=8,
        id="websub_renew",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "yt_update=5min | bili_update=2min"
        " | bili_sync_ch=24h | channel_refresh=24h"
        " | daily_backfill=04:00 | websub_renew=每8天"
    )
