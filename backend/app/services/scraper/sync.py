import asyncio
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.models.models import Channel, Organization, Platform
from app.integrations.youtube import get_youtube_sync_service
from app.database import session_scope
from app.loguru_config import logger
from app.services.api_key_manager import is_api_available
from .base import VtuberChannel
from .vspo_wiki import VSPO_ORG_NAME
from .nijisanji_wiki import NIJISANJI_ORG_NAME
from app.constants import ChannelStatus

class ScraperError(Exception):
    """业务逻辑基础异常"""
    pass

class ProviderQuotaError(ScraperError):
    """API 配额耗尽 (不可重试，需中断任务)"""
    pass

class DataValidationError(ScraperError):
    """数据校验失败或资源不存在 (不可重试，跳过当前)"""
    pass

class TransientError(Exception):
    """瞬时环境错误 (可重试：如网络超时、502/503)"""
    pass

# --- Tenacity 重试配置 ---

# 针对网络抖动的重试策略：重试3次，等待 2s, 4s, 8s
network_retry_policy = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type((TransientError, OperationalError)),
    before_sleep=before_sleep_log(logger, "DEBUG"),
    reraise=True
)

# --- 业务逻辑重构 ---

async def sync_wiki_channels(
    vtuber_channels: list[VtuberChannel],
    org_name: str,
    db: AsyncSession,
) -> dict:
    """同步指定组织的频道列表"""
    stats = {"created": 0, "updated": 0, "skipped": 0, "failed": 0}
    channels_to_sync: list[int] = []

    try:
        # 1. 获取或创建组织 (系统级操作，失败直接抛出)
        result = await db.execute(select(Organization).where(Organization.name == org_name))
        org = result.scalar_one_or_none()
        if not org:
            org = Organization(name=org_name)
            db.add(org)
            await db.flush()
            logger.info(f"Created organization: {org_name}")

        # 2. 迭代处理频道
        for vtuber_ch in vtuber_channels:
            try:
                res_type, channel_id = await _sync_single_channel(vtuber_ch, org.id, db)
                
                if res_type == "created" and channel_id:
                    channels_to_sync.append(channel_id)
                stats[res_type] += 1

            except DataValidationError as e:
                # 预期的业务数据问题：记录并跳过
                logger.warning(f"跳过频道 {vtuber_ch.name}: {e}")
                stats["skipped"] += 1
            except ProviderQuotaError:
                # API 配额问题：抛出给上层触发熔断
                raise
            except Exception as e:
                # 未知错误：记录详细堆栈，防止因单个数据导致整个批次崩溃
                logger.exception(f"同步频道 {vtuber_ch.name} 时发生非预期错误: {e}")
                stats["failed"] += 1

        # 3. 提交本组织的所有更改
        await db.commit()

    except (SQLAlchemyError, ProviderQuotaError) as e:
        # 数据库故障或配额故障：属于系统性异常，回滚并上抛
        await db.rollback()
        logger.error(f"组织 {org_name} 同步发生系统级故障，已回滚: {e}")
        raise
    except Exception as e:
        await db.rollback()
        logger.critical(f"sync_wiki_channels 发生未捕获异常: {e}")
        raise

    # 4. 触发后台视频同步 (异步)
    if channels_to_sync and await is_api_available():
        asyncio.create_task(
            _batch_sync_new_channels(channels_to_sync),
            name=f"v_sync_{org_name}_{len(channels_to_sync)}"
        )

    return stats

async def _sync_single_channel(
    vtuber_ch: VtuberChannel,
    org_id: int,
    db: AsyncSession,
) -> Tuple[str, Optional[int]]:
    """处理单个频道的同步逻辑"""
    
    # 解析 Channel ID (带重试)
    channel_id = vtuber_ch.youtube_channel_id
    if not channel_id and vtuber_ch.youtube_handle:
        channel_id = await _resolve_handle_with_retry(vtuber_ch.youtube_handle)
        if channel_id:
            vtuber_ch.youtube_channel_id = channel_id

    if not channel_id:
        raise DataValidationError(f"无法解析 YouTube ID: {vtuber_ch.name} (@{vtuber_ch.youtube_handle})")

    # 查询现有记录
    result = await db.execute(
        select(Channel).where(
            Channel.channel_id == channel_id,
            Channel.platform == Platform.YOUTUBE,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # 更新逻辑
        is_updated = _update_channel_attributes(existing, vtuber_ch)
        if is_updated:
            await db.flush()
            return "updated", existing.id
        return "skipped", None

    # 创建逻辑：调用 API 获取详情 (带重试)
    yt_info = await _fetch_youtube_info_with_retry(channel_id)
    if not yt_info:
        raise DataValidationError(f"YouTube API 未返回有效数据: {channel_id}")

    new_channel = Channel(
        org_id=org_id,
        platform=Platform.YOUTUBE,
        channel_id=channel_id,
        name=vtuber_ch.name,
        avatar_url=yt_info.get("avatar_url"),
        banner_url=yt_info.get("banner_url"),
        description=yt_info.get("description"),
        twitter_url=vtuber_ch.twitter_url,
        youtube_url=f"https://www.youtube.com/channel/{channel_id}",
        twitch_url=vtuber_ch.twitch_url,
        group=vtuber_ch.group,
        status=vtuber_ch.status or ChannelStatus.ACTIVE,
    )
    db.add(new_channel)
    await db.flush()
    return "created", new_channel.id

# --- 受保护的 API 调用层 (结合 Tenacity) ---

@network_retry_policy
async def _resolve_handle_with_retry(handle: str) -> Optional[str]:
    """通过 Handle 获取 Channel ID"""
    try:
        yt_service = get_youtube_sync_service()
        return await yt_service.resolve_channel_id(handle)
    except Exception as e:
        _classify_api_exception(e, f"ResolveHandle:{handle}")
        return None

@network_retry_policy
async def _fetch_youtube_info_with_retry(channel_id: str) -> Optional[dict]:
    """获取频道元数据"""
    try:
        yt_service = get_youtube_sync_service()
        return await yt_service.get_channel_info(channel_id)
    except Exception as e:
        _classify_api_exception(e, f"GetChannelInfo:{channel_id}")
        return None

def _classify_api_exception(e: Exception, context: str):
    """
    将原始异常分类为自定义异常。
    如果是 403 Quota -> ProviderQuotaError (不重试)
    如果是 Timeout/5xx -> TransientError (触发重试)
    """
    msg = str(e).lower()
    if "quotaexceeded" in msg or "403" in msg:
        raise ProviderQuotaError(f"API 配额耗尽: {context}")
    
    if any(x in msg for x in ["timeout", "connection", "502", "503", "504"]):
        raise TransientError(f"网络瞬时故障: {context} - {e}")
    
    # 默认作为非重试业务错误记录
    logger.warning(f"API 业务调用失败: {context} - {e}")

# --- 工具函数 ---

def _update_channel_attributes(existing: Channel, vtuber_ch: VtuberChannel) -> bool:
    """同步更新频道字段"""
    updated = False
    fields = [
        ('twitter_url', vtuber_ch.twitter_url),
        ('twitch_url', vtuber_ch.twitch_url),
        ('name', vtuber_ch.name),
        ('group', vtuber_ch.group)
    ]
    for attr, new_val in fields:
        if new_val and getattr(existing, attr) != new_val:
            setattr(existing, attr, new_val)
            updated = True
            
    if vtuber_ch.status and existing.status != vtuber_ch.status:
        existing.status = vtuber_ch.status
        if vtuber_ch.status == ChannelStatus.GRADUATED:
            existing.is_active = False
        updated = True
    return updated

async def _batch_sync_new_channels(channel_ids: list[int]) -> None:
    """死信队列逻辑：若此后台任务失败，应写入日志并保持可追溯"""
    yt_service = get_youtube_sync_service()
    for channel_id in channel_ids:
        try:
            async with session_scope() as session:
                ch = await session.get(Channel, channel_id)
                if ch:
                    # 内部已带重试的 API 调用
                    await yt_service.sync_channel_videos(session, ch, full_refresh=True)
                    logger.info(f"新频道视频同步完成: {ch.name}")
            await asyncio.sleep(1.0)
        except Exception as e:
            # 此处即为死信处理：记录 Error 级别日志，包含所有必要 ID
            logger.error(f"CRITICAL: 新频道视频同步失败 [DLQ Candidate] channel_id={channel_id}: {e}")

# --- 入口函数 ---

async def scrape_and_sync_all(db: AsyncSession) -> dict:
    """爬虫主入口：实现组织间的熔断"""
    all_stats = {"vspo": {}, "nijisanji": {}}
    
    tasks = [
        ("vspo", VSPO_ORG_NAME, scrape_and_sync_vspo),
        ("nijisanji", NIJISANJI_ORG_NAME, scrape_and_sync_nijisanji)
    ]

    for key, org_name, func in tasks:
        try:
            all_stats[key] = await func(db)
        except ProviderQuotaError:
            logger.critical("检测到 API 配额耗尽，熔断后续所有同步任务。")
            break # 停止后续组织的爬取
        except Exception as e:
            logger.error(f"组织 {org_name} 同步发生致命错误: {e}")
            all_stats[key] = {"error": str(e)}
            
    return all_stats

async def scrape_and_sync_vspo(db: AsyncSession) -> dict:
    from .vspo_wiki import VSPOWikiScraper
    scraper = VSPOWikiScraper()
    try:
        channels = await scraper.scrape()
        return await sync_wiki_channels(channels, VSPO_ORG_NAME, db)
    finally:
        await scraper.close()

async def scrape_and_sync_nijisanji(db: AsyncSession) -> dict:
    from .nijisanji_wiki import NijisanjiWikiScraper
    scraper = NijisanjiWikiScraper()
    try:
        channels = await scraper.scrape()
        return await sync_wiki_channels(channels, NIJISANJI_ORG_NAME, db)
    finally:
        await scraper.close()