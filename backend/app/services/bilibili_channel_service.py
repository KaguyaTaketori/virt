from dataclasses import dataclass
from typing import Optional
from bilibili_api import Credential
from sqlalchemy.ext.asyncio import AsyncSession

from app.loguru_config import logger
from app.models.models import Channel, User
from app.integrations.bili_client import BiliClient
from app.schemas.schemas import BiliDynamic, BiliVideo


@dataclass
class BilibiliChannelData:
    info: Optional[dict]
    dynamics: list
    videos: list
    next_offset: str


@dataclass
class BilibiliChannelInfo:
    mid: int
    name: str
    face: Optional[str]
    sign: Optional[str]
    fans: Optional[int]
    attention: Optional[int]
    archive_count: Optional[int]


@dataclass
class BilibiliVideosData:
    videos: list
    total: int


@dataclass
class BilibiliDynamicsData:
    dynamics: list
    next_offset: str


def _resolve_credential(
    current_user: Optional["User"],
    client: BiliClient,
) -> Optional[Credential]:
    if current_user and current_user.bilibili_sessdata:
        try:
            from bilibili_api import Credential

            return Credential(
                sessdata=current_user.bilibili_sessdata,
                bili_jct=current_user.bilibili_bili_jct,
                buvid3=current_user.bilibili_buvid3,
            )
        except Exception:
            pass
    return client._create_credential()


# backend/app/services/bilibili_channel_service.py
async def fetch_bilibili_channel_data(
    db: AsyncSession,
    channel: Channel,
    credential: Optional[Credential],
    client: BiliClient,
    dynamics_offset: str = "",
    dynamics_limit: int = 12,
) -> BilibiliChannelData:
    uid = channel.channel_id

    # 1. 获取视频列表
    videos: list[BiliVideo] = []
    try:
        raw = await client.get_videos(uid, credential=credential, page=1, page_size=30)
        videos = [client._parse_video(v) for v in raw.get("list", {}).get("vlist", [])]
    except Exception as e:
        logger.warning("获取 B 站视频列表失败 uid={}: {}", uid, e)

    # 2. 获取动态（仅在有凭证时尝试）
    dynamics: list[BiliDynamic] = []
    next_offset: str = ""
    if credential:
        try:
            dynamics, next_offset = await client.get_dynamics(
                uid, offset=dynamics_offset, credential=credential
            )
            # ✅ 移除对不存在的 upsert_dynamics 的调用
            # 动态持久化由独立的定时任务负责，不在请求链路中处理
        except Exception as e:
            logger.warning("获取 B 站动态失败 uid={}: {}", uid, e)

    # 3. 获取并刷新频道信息（✅ 传递 credential）
    info_obj = await client.get_channel_info(uid, credential=credential)
    if info_obj:
        channel.bilibili_face = info_obj.face or channel.bilibili_face
        channel.bilibili_sign = info_obj.sign or channel.bilibili_sign
        channel.bilibili_fans = info_obj.fans or channel.bilibili_fans
        channel.bilibili_archive_count = (
            info_obj.archive_count or channel.bilibili_archive_count
        )
        await db.commit()

    info_dict = {
        "mid": uid,
        "name": channel.name,
        "face": channel.bilibili_face,
        "sign": channel.bilibili_sign,
        "fans": channel.bilibili_fans,
        "attention": channel.bilibili_following,
        "archive_count": channel.bilibili_archive_count,
    }
    return BilibiliChannelData(
        info=info_dict,
        dynamics=dynamics,
        videos=videos,
        next_offset=next_offset,
    )


async def fetch_bilibili_info(
    db: AsyncSession,
    channel: Channel,
    credential: Optional[Credential],
    client: BiliClient,
) -> BilibiliChannelInfo:
    uid = channel.channel_id
    info_obj = await client.get_channel_info(uid, credential=credential)
    if info_obj:
        channel.bilibili_face = info_obj.face or channel.bilibili_face
        channel.bilibili_sign = info_obj.sign or channel.bilibili_sign
        channel.bilibili_fans = info_obj.fans or channel.bilibili_fans
        channel.bilibili_archive_count = (
            info_obj.archive_count or channel.bilibili_archive_count
        )
        await db.commit()

    return BilibiliChannelInfo(
        mid=uid,
        name=channel.name,
        face=channel.bilibili_face,
        sign=channel.bilibili_sign,
        fans=channel.bilibili_fans,
        attention=channel.bilibili_following,
        archive_count=channel.bilibili_archive_count,
    )


async def fetch_bilibili_videos(
    channel: Channel,
    credential: Optional[Credential],
    client: BiliClient,
    page: int = 1,
    page_size: int = 30,
) -> BilibiliVideosData:
    uid = channel.channel_id
    videos: list[BiliVideo] = []
    total = 0
    try:
        raw = await client.get_videos(
            uid, credential=credential, page=page, page_size=page_size
        )
        videos = [client._parse_video(v) for v in raw.get("list", {}).get("vlist", [])]
        total = raw.get("list", {}).get("count", 0) or len(videos)
    except Exception as e:
        logger.warning("获取 B 站视频列表失败 uid={}: {}", uid, e)

    return BilibiliVideosData(videos=videos, total=total)


async def fetch_bilibili_dynamics(
    channel: Channel,
    credential: Optional[Credential],
    client: BiliClient,
    offset: str = "",
    limit: int = 12,
) -> BilibiliDynamicsData:
    uid = channel.channel_id
    dynamics: list[BiliDynamic] = []
    next_offset: str = ""
    if credential:
        try:
            dynamics, next_offset = await client.get_dynamics(
                uid, offset=offset, credential=credential
            )
        except Exception as e:
            logger.warning("获取 B 站动态失败 uid={}: {}", uid, e)

    return BilibiliDynamicsData(dynamics=dynamics, next_offset=next_offset)
