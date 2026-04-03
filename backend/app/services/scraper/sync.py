import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.models.models import Channel, Organization, Platform
from app.services.youtube_channel import get_youtube_channel_info
from app.services.youtube_sync import sync_channel_videos
from app.database import SessionLocal
from .base import VtuberChannel
from .vspo_wiki import VSPO_ORG_NAME
from .nijisanji_wiki import NIJISANJI_ORG_NAME

logger = logging.getLogger(__name__)


async def sync_wiki_channels(
    vtuber_channels: list[VtuberChannel],
    org_name: str,
    db: Session,
) -> dict:
    """
    将爬取的VTuber频道同步到数据库

    返回统计信息
    """
    stats = {"created": 0, "updated": 0, "skipped": 0}

    # 获取或创建组织
    org = db.query(Organization).filter(Organization.name == org_name).first()
    if not org:
        org = Organization(name=org_name)
        db.add(org)
        db.flush()
        logger.info(f"Created organization: {org_name}")

    for vtuber_ch in vtuber_channels:
        try:
            result = await _sync_single_channel(vtuber_ch, org.id, db)
            if result == "created":
                stats["created"] += 1
            elif result == "updated":
                stats["updated"] += 1
            else:
                stats["skipped"] += 1
        except Exception as e:
            logger.warning(f"Failed to sync channel {vtuber_ch.name}: {e}")
            stats["skipped"] += 1

    return stats


async def _sync_single_channel(
    vtuber_ch: VtuberChannel,
    org_id: int,
    db: Session,
) -> str:
    """同步单个频道"""
    # 解析YouTube channel_id
    channel_id = vtuber_ch.youtube_channel_id
    if not channel_id and vtuber_ch.youtube_handle:
        channel_id = await _resolve_handle(vtuber_ch.youtube_handle)
        if channel_id:
            vtuber_ch.youtube_channel_id = channel_id

    if not channel_id:
        logger.debug(f"Cannot resolve channel_id for {vtuber_ch.name}")
        return "skipped"

    # 查询已存在
    existing = (
        db.query(Channel)
        .filter(
            Channel.channel_id == channel_id,
            Channel.platform == Platform.YOUTUBE,
        )
        .first()
    )

    if existing:
        # 更新链接字段
        updated = False
        if vtuber_ch.twitter_url and existing.twitter_url != vtuber_ch.twitter_url:
            existing.twitter_url = vtuber_ch.twitter_url
            updated = True
        if vtuber_ch.twitch_url and existing.twitch_url != vtuber_ch.twitch_url:
            existing.twitch_url = vtuber_ch.twitch_url
            updated = True
        if vtuber_ch.name and existing.name != vtuber_ch.name:
            existing.name = vtuber_ch.name
            updated = True
        if vtuber_ch.group and existing.group != vtuber_ch.group:
            existing.group = vtuber_ch.group
            updated = True
        if vtuber_ch.status and existing.status != vtuber_ch.status:
            existing.status = vtuber_ch.status
            updated = True

        if updated:
            db.flush()
            logger.debug(f"Updated channel: {vtuber_ch.name}")
            return "updated"
        return "skipped"

    # 获取YouTube频道详情（头像等）
    yt_info = await _fetch_youtube_info(channel_id)

    # 创建新频道
    new_channel = Channel(
        org_id=org_id,
        platform=Platform.YOUTUBE,
        channel_id=channel_id,
        name=vtuber_ch.name,
        avatar_url=yt_info.get("avatar_url") if yt_info else None,
        twitter_url=vtuber_ch.twitter_url,
        youtube_url=f"https://www.youtube.com/channel/{channel_id}",
        twitch_url=vtuber_ch.twitch_url,
        group=vtuber_ch.group,
        status=vtuber_ch.status or "active",
    )
    db.add(new_channel)
    db.flush()
    logger.info(f"Created channel: {vtuber_ch.name} ({channel_id})")

    # 创建后立即同步视频
    try:
        from app.database_async import AsyncSessionFactory
        from app.config import settings

        async with AsyncSessionFactory() as session:
            ch_obj = await session.get(Channel, new_channel.id)
            if ch_obj and settings.youtube_api_key:
                from app.services.youtube_sync import sync_channel_videos

                await sync_channel_videos(
                    session, ch_obj, settings.youtube_api_key, full_refresh=True
                )
                logger.info(f"Synced videos for channel: {vtuber_ch.name}")
    except Exception as e:
        logger.warning(f"Failed to sync videos for {vtuber_ch.name}: {e}")

    return "created"


async def _resolve_handle(handle: str) -> Optional[str]:
    """将 @username 解析为 channel_id"""
    try:
        from app.services.youtube_channel import resolve_youtube_channel

        return await resolve_youtube_channel(handle)
    except Exception as e:
        logger.warning(f"Failed to resolve handle {handle}: {e}")
        return None


async def _fetch_youtube_info(channel_id: str) -> Optional[dict]:
    """获取YouTube频道详情"""
    try:
        return await get_youtube_channel_info(channel_id)
    except Exception as e:
        logger.warning(f"Failed to fetch YouTube info for {channel_id}: {e}")
        return None


async def scrape_and_sync_vspo(db: Session) -> dict:
    """爬取并同步VSPO!频道"""
    from .vspo_wiki import VSPOWikiScraper

    scraper = VSPOWikiScraper()
    try:
        channels = await scraper.scrape()
        return await sync_wiki_channels(channels, VSPO_ORG_NAME, db)
    finally:
        await scraper.close()


async def scrape_and_sync_nijisanji(db: Session) -> dict:
    """爬取并同步Nijisanji频道"""
    from .nijisanji_wiki import NijisanjiWikiScraper

    scraper = NijisanjiWikiScraper()
    try:
        channels = await scraper.scrape()
        return await sync_wiki_channels(channels, NIJISANJI_ORG_NAME, db)
    finally:
        await scraper.close()


async def scrape_and_sync_all(db: Session) -> dict:
    """爬取并同步所有支持的VTuber Wiki"""
    all_stats = {"vspo": {}, "nijisanji": {}}

    # VSPO!
    try:
        all_stats["vspo"] = await scrape_and_sync_vspo(db)
    except Exception as e:
        logger.error(f"Failed to scrape VSPO!: {e}")
        all_stats["vspo"] = {"error": str(e)}

    # Nijisanji
    try:
        all_stats["nijisanji"] = await scrape_and_sync_nijisanji(db)
    except Exception as e:
        logger.error(f"Failed to scrape Nijisanji: {e}")
        all_stats["nijisanji"] = {"error": str(e)}

    return all_stats


async def scheduled_scrape_all():
    """定时任务：爬取并同步所有VTuber Wiki（使用SessionLocal）"""
    db = SessionLocal()
    try:
        return await scrape_and_sync_all(db)
    finally:
        db.close()
