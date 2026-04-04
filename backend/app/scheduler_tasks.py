from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import STATE_STOPPED
import httpx
from app.loguru_config import logger
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database_async import AsyncSessionFactory
from app.models.models import Channel, Stream, StreamStatus, Platform, Video
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
import asyncio

scheduler = AsyncIOScheduler(timezone="UTC")


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
    callback_url = settings.websub_callback_url
    await subscribe_all_active_channels(callback_url)


async def discover_youtube_streams():
    """
    Search-based stream discovery 已禁用。

    现在的策略：
    - 更新已知活跃流：用 videos.list（update_youtube_streams）
    - 查询"正在直播"：在 API 层按需用 youtube_sync 增量拉取
    """
    return


async def update_youtube_streams():
    """
    用 videos.list（1配额/次）刷新已知活跃流的状态。
    配额消耗极低，只要有剩余就跑。
    """
    if not settings.youtube_api_key:
        return

    if not await can_spend("videos.list", 1):
        logger.info("配额耗尽，跳过")
        return

    async with AsyncSessionFactory() as db:
        result = await db.execute(
            select(Stream).where(
                Stream.platform == Platform.YOUTUBE,
                Stream.status.in_([StreamStatus.LIVE, StreamStatus.UPCOMING]),
                Stream.video_id.isnot(None),
            )
        )
        active = result.scalars().all()

        if not active:
            return

        vid_to_ch_id = {s.video_id: s.channel_id for s in active}
        video_ids = list(vid_to_ch_id.keys())

        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(0, len(video_ids), 50):
                chunk = video_ids[i : i + 50]
                if not await can_spend("videos.list", 1):
                    logger.info("配额耗尽，停止当前批次")
                    break
                items = await get_videos_details(client, chunk)
                await spend("videos.list", 1)
                for item in items:
                    parsed = parse_youtube_stream(item)
                    if parsed and parsed["video_id"] in vid_to_ch_id:
                        await _async_upsert_stream(
                            db,
                            vid_to_ch_id[parsed["video_id"]],
                            parsed,
                            Platform.YOUTUBE,
                        )

        await db.commit()
        logger.info(
            "刷新 {} 条 | 配额剩余 {}", len(active), quota_status()["remaining"]
        )


async def _async_upsert_stream(
    db: AsyncSession, channel_id: int, parsed: dict, platform
):
    """异步版本的 upsert，供调度器使用。"""
    from app.models.models import Stream

    result = await db.execute(
        select(Stream).where(
            Stream.channel_id == channel_id,
            Stream.video_id == parsed["video_id"],
        )
    )
    stream = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if not stream:
        stream = Stream(channel_id=channel_id, platform=platform)
        db.add(stream)

    for field, value in parsed.items():
        if getattr(stream, field, None) != value:
            setattr(stream, field, value)

    stream.updated_at = now
    if parsed.get("viewer_count", 0) > (stream.peak_viewers or 0):
        stream.peak_viewers = parsed["viewer_count"]


async def update_bilibili_streams():
    """使用 AsyncSession，与 YouTube 任务保持一致。"""
    async with AsyncSessionFactory() as db:
        result = await db.execute(
            select(Channel).where(
                Channel.platform == Platform.BILIBILI,
                Channel.is_active.is_(True),
            )
        )
        channels = result.scalars().all()
        if not channels:
            return

        uid_to_ch_id = {ch.channel_id: ch.id for ch in channels}
        uids = list(uid_to_ch_id.keys())

    async with httpx.AsyncClient(timeout=30.0) as client:
        rooms_data = await get_rooms_by_uids(client, uids)

    async with AsyncSessionFactory() as db:
        for uid, room_data in rooms_data.items():
            if uid in uid_to_ch_id:
                parsed = parse_bilibili_room(room_data)
                await _async_upsert_stream(
                    db, uid_to_ch_id[uid], parsed, Platform.BILIBILI
                )
        await db.commit()
        logger.info("更新 {} 个房间", len(rooms_data))


async def sync_bilibili_channels():
    async with AsyncSessionFactory() as db:
        result = await db.execute(
            select(Channel).where(
                Channel.platform == Platform.BILIBILI,
                Channel.is_active == True,
            )
        )
        channels = result.scalars().all()
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

                if info.get("fans") is not None:
                    ch.bilibili_fans = info["fans"]
                    changed = True
                if info.get("sign"):
                    ch.bilibili_sign = info["sign"]
                    changed = True
                if info.get("archive_count") is not None:
                    ch.bilibili_archive_count = info["archive_count"]
                    changed = True
                if info.get("avatar_url"):
                    ch.bilibili_face = info["avatar_url"]
                    changed = True
                if info.get("attention") is not None:
                    ch.bilibili_following = info["attention"]
                    changed = True

                if changed:
                    ch.updated_at = datetime.now(timezone.utc)

                total_synced = await sync_bilibili_channel_videos(
                    db, ch.id, ch.channel_id
                )
                if total_synced > 0:
                    logger.info("{}: 同步了 {} 个视频", ch.name, total_synced)

        await db.commit()
        logger.info("同步 {} 个频道信息", len(channels))


async def refresh_channel_details():
    """每天执行，刷新所有频道的 banner/描述/链接"""
    if not settings.youtube_api_key:
        return

    async with AsyncSessionFactory() as db:
        result = await db.execute(
            select(Channel).where(
                Channel.platform == Platform.YOUTUBE,
                Channel.is_active == True,
            )
        )
        channels = result.scalars().all()

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

        await db.commit()
        logger.info("完成")


async def sync_youtube_videos_bulk(limit: int = 50):
    """批量同步历史视频 - 每次处理limit个频道，轮流处理所有频道"""
    if not settings.youtube_api_key:
        return

    from app.services.youtube_sync import sync_channel_videos

    # 获取当前是第几轮（基于时间）
    import time

    round_num = int(time.time()) // 3600 % 10  # 每小时换一轮，最多记住10小时

    async with AsyncSessionFactory() as db:
        # 获取频道总数
        result = await db.execute(
            select(Channel).where(
                Channel.platform == Platform.YOUTUBE,
                Channel.is_active == True,
            )
        )
        all_channels = result.scalars().all()
        total_channels = len(all_channels)

        if total_channels == 0:
            return

        # 计算偏移量，实现轮流处理
        offset = (round_num * limit) % total_channels
        channels = all_channels[offset : offset + limit]
        if len(channels) < limit:
            channels.extend(all_channels[: limit - len(channels)])

        if not channels:
            return

        logger.info(
            "开始批量同步 {} 个频道的视频 (round={}, offset={})",
            len(channels),
            round_num,
            offset,
        )

        for ch in channels:
            try:
                await sync_channel_videos(
                    db, ch, settings.youtube_api_key, full_refresh=False
                )
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning(f"{ch.name}: {e}")

        logger.info("批量同步完成")


async def discover_yive_streams_from_videos():
    """从频道视频列表发现 live/upcoming  streams（无搜索API时的备选方案）"""
    if not settings.youtube_api_key:
        return

    from app.services.youtube_utils import determine_video_status

    async with AsyncSessionFactory() as db:
        # 获取最近7天有视频的频道
        result = await db.execute(
            select(Channel).where(
                Channel.platform == Platform.YOUTUBE,
                Channel.is_active == True,
            )
        )
        channels = result.scalars().all()

        if not channels:
            return

        logger.info("从 {} 个频道发现 live streams", len(channels))

        async with httpx.AsyncClient(timeout=30.0) as client:
            for ch in channels:
                # 获取该频道最近上传的视频（可能包含 live）
                result = await db.execute(
                    select(Video).where(
                        Video.channel_id == ch.id,
                        Video.status.in_(["live", "upcoming"]),
                    )
                )
                live_videos = result.scalars().all()

                for video in live_videos:
                    await _async_upsert_stream(
                        db,
                        ch.id,
                        {
                            "video_id": video.video_id,
                            "title": video.title,
                            "thumbnail_url": video.thumbnail_url,
                            "platform": "YOUTUBE",
                            "status": video.status.upper() if video.status else "LIVE",
                            "scheduled_at": video.scheduled_at,
                            "live_started_at": video.live_started_at,
                            "viewer_count": 0,
                        },
                        Platform.YOUTUBE,
                    )

        await db.commit()
        logger.info("Live streams 发现完成")


def start_scheduler():
    if scheduler.state != STATE_STOPPED:
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
    # 每小时批量同步50个频道的视频（快速增量）
    scheduler.add_job(
        sync_youtube_videos_bulk,
        "interval",
        minutes=60,
        id="yt_bulk_sync",
        next_run_time=now,
        replace_existing=True,
    )
    # 每5分钟从视频列表发现 live streams
    scheduler.add_job(
        discover_yive_streams_from_videos,
        "interval",
        minutes=5,
        id="yt_live_discover",
        replace_existing=True,
    )
    logger.info(
        "yt_discover=已禁用 | yt_update=5min | bili_update=2min | yt_bulk_sync=60min | yt_live_discover=5min"
    )

    scheduler.add_job(
        _daily_backfill_sync,
        "cron",
        hour=4,
        minute=0,
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

    from app.services.scraper import sync as scraper_sync

    scheduler.add_job(
        scraper_sync.scheduled_scrape_all,
        "cron",
        hour=2,
        minute=0,
        day_of_week=6,
        id="wiki_scrape_weekly",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "yt_update=5min | bili_update=2min"
        " | bili_sync_ch=24h | channel_refresh=24h"
        " | daily_backfill=04:00 | websub_renew=每8天"
        " | wiki_scrape=每周日02:00"
    )
