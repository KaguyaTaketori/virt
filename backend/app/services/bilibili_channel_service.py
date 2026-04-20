from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Optional
from bilibili_api import Credential
from sqlalchemy.ext.asyncio import AsyncSession

from app.loguru_config import logger
from app.models.models import Channel, User, Video, BilibiliDynamic
from app.integrations.bili_client import BiliClient
from app.schemas.schemas import BiliDynamic, BiliVideo
from app.repositories import VideoRepository, BilibiliDynamicRepository


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


def _video_to_bilivideo(video: Video) -> BiliVideo:
    return BiliVideo(
        bvid=video.video_id,
        title=video.title or "",
        pic=video.thumbnail_url or "",
        duration=video.duration or "",
        pubdate=int(video.published_at.timestamp()) if video.published_at else 0,
        play=video.view_count or 0,
        like=video.like_count or 0,
        reply=0,
    )


def _dynamic_to_bili_dynamic(dynamic: BilibiliDynamic) -> BiliDynamic:
    content_nodes = []
    images = []
    stat = {}

    if dynamic.content_nodes:
        try:
            content_nodes = json.loads(dynamic.content_nodes)
        except (json.JSONDecodeError, TypeError):
            pass

    if dynamic.images:
        try:
            images = json.loads(dynamic.images)
        except (json.JSONDecodeError, TypeError):
            pass

    if dynamic.stat:
        try:
            stat = json.loads(dynamic.stat)
        except (json.JSONDecodeError, TypeError):
            pass

    return BiliDynamic(
        dynamic_id=dynamic.dynamic_id,
        uid=dynamic.uid or "",
        uname=dynamic.uname or "",
        face=dynamic.face,
        type=dynamic.type or 0,
        content_nodes=content_nodes,
        images=images,
        repost_content=dynamic.repost_content,
        timestamp=dynamic.timestamp or 0,
        url=dynamic.url,
        topic=dynamic.topic,
        is_top=dynamic.is_top or False,
        stat=stat,
    )


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


async def fetch_bilibili_channel_data(
    db: AsyncSession,
    channel: Channel,
    credential: Optional[Credential],
    client: BiliClient,
    dynamics_offset: str = "",
    dynamics_limit: int = 12,
) -> BilibiliChannelData:
    uid = channel.channel_id

    video_repo = VideoRepository(db)
    dynamic_repo = BilibiliDynamicRepository(db)

    # 1. 获取视频列表
    videos: list[BiliVideo] = []
    try:
        raw = await client.get_videos(uid, credential=credential, page=1, page_size=30)
        vlist = raw.get("list", {}).get("vlist", [])
        videos = [client._parse_video(v) for v in vlist]

        await video_repo.batch_upsert_bilibili(channel.id, videos)
        await db.commit()
    except Exception as e:
        logger.warning("获取 B 站视频列表失败 uid={}: {}", uid, e)
        db_videos = await video_repo.get_paginated_by_channel(
            channel_id=channel.id,
            page=1,
            page_size=30,
        )
        videos = [_video_to_bilivideo(v) for v in db_videos[0]]

    # 2. 获取动态（仅在有凭证时尝试）
    dynamics: list[BiliDynamic] = []
    next_offset: str = ""
    if credential:
        try:
            dynamics, next_offset = await client.get_dynamics(
                uid, offset=dynamics_offset, credential=credential
            )

            for d in dynamics:
                await dynamic_repo.upsert_dynamic(
                    channel_id=channel.id,
                    dynamic_id=d.dynamic_id,
                    data={
                        "channel_id": channel.id,
                        "dynamic_id": d.dynamic_id,
                        "uid": d.uid,
                        "uname": d.uname,
                        "face": d.face,
                        "type": d.type,
                        "content_nodes": json.dumps(
                            d.content_nodes, ensure_ascii=False
                        ),
                        "images": json.dumps(d.images, ensure_ascii=False),
                        "repost_content": d.repost_content,
                        "timestamp": d.timestamp,
                        "published_at": datetime.fromtimestamp(
                            d.timestamp, tz=timezone.utc
                        )
                        if d.timestamp
                        else None,
                        "url": d.url,
                        "stat": json.dumps(d.stat, ensure_ascii=False),
                        "topic": d.topic,
                        "is_top": d.is_top,
                    },
                )
            await db.commit()
        except Exception as e:
            logger.warning("获取 B 站动态失败 uid={}: {}", uid, e)
            db_dynamics = await dynamic_repo.get_by_channel(
                channel_id=channel.id,
                limit=dynamics_limit,
            )
            dynamics = [_dynamic_to_bili_dynamic(d) for d in db_dynamics]
            next_offset = ""

    # 3. 获取并刷新频道信息
    info_obj = await client.get_channel_info(uid, credential=credential)
    if info_obj:
        channel.avatar_url = info_obj.face or channel.avatar_url
        channel.bio = info_obj.sign or channel.bio
        channel.follower_count = info_obj.fans or channel.follower_count
        channel.video_count = info_obj.archive_count or channel.video_count
        await db.commit()

    info_dict = {
        "mid": uid,
        "name": channel.name,
        "face": channel.avatar_url,
        "sign": channel.bio,
        "fans": channel.follower_count,
        "attention": channel.following_count,
        "archive_count": channel.video_count,
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
        channel.avatar_url = info_obj.face or channel.avatar_url
        channel.bio = info_obj.sign or channel.bio
        channel.follower_count = info_obj.fans or channel.follower_count
        channel.video_count = info_obj.archive_count or channel.video_count
        await db.commit()

    return BilibiliChannelInfo(
        mid=uid,
        name=channel.name,
        face=channel.avatar_url,
        sign=channel.bio,
        fans=channel.follower_count,
        attention=channel.following_count,
        archive_count=channel.video_count,
    )


async def fetch_bilibili_videos(
    db: AsyncSession,
    channel: Channel,
    credential: Optional[Credential],
    client: BiliClient,
    page: int = 1,
    page_size: int = 30,
) -> BilibiliVideosData:
    uid = channel.channel_id
    videos: list[BiliVideo] = []
    total = 0

    video_repo = VideoRepository(db)

    try:
        raw = await client.get_videos(
            uid, credential=credential, page=page, page_size=page_size
        )
        vlist = raw.get("list", {}).get("vlist", [])
        videos = [client._parse_video(v) for v in vlist]
        total = raw.get("list", {}).get("count", 0) or len(videos)

        await video_repo.batch_upsert_bilibili(channel.id, videos)
        await db.commit()
    except Exception as e:
        logger.warning("获取 B 站视频列表失败 uid={}: {}", uid, e)
        db_videos = await video_repo.get_paginated_by_channel(
            channel_id=channel.id,
            page=page,
            page_size=page_size,
        )
        videos = [_video_to_bilivideo(v) for v in db_videos[0]]
        total = db_videos[1]

    return BilibiliVideosData(videos=videos, total=total)


async def fetch_bilibili_dynamics(
    db: AsyncSession,
    channel: Channel,
    credential: Optional[Credential],
    client: BiliClient,
    offset: str = "",
    limit: int = 12,
) -> BilibiliDynamicsData:
    uid = channel.channel_id
    dynamics: list[BiliDynamic] = []
    next_offset: str = ""

    dynamic_repo = BilibiliDynamicRepository(db)

    if credential:
        try:
            dynamics, next_offset = await client.get_dynamics(
                uid, offset=offset, credential=credential
            )

            for d in dynamics:
                await dynamic_repo.upsert_dynamic(
                    channel_id=channel.id,
                    dynamic_id=d.dynamic_id,
                    data={
                        "channel_id": channel.id,
                        "dynamic_id": d.dynamic_id,
                        "uid": d.uid,
                        "uname": d.uname,
                        "face": d.face,
                        "type": d.type,
                        "content_nodes": json.dumps(
                            d.content_nodes, ensure_ascii=False
                        ),
                        "images": json.dumps(d.images, ensure_ascii=False),
                        "repost_content": d.repost_content,
                        "timestamp": d.timestamp,
                        "published_at": datetime.fromtimestamp(
                            d.timestamp, tz=timezone.utc
                        )
                        if d.timestamp
                        else None,
                        "url": d.url,
                        "stat": json.dumps(d.stat, ensure_ascii=False),
                        "topic": d.topic,
                        "is_top": d.is_top,
                    },
                )
            await db.commit()
        except Exception as e:
            logger.warning("获取 B 站动态失败 uid={}: {}", uid, e)
            db_dynamics = await dynamic_repo.get_by_channel(
                channel_id=channel.id,
                limit=limit,
            )
            dynamics = [_dynamic_to_bili_dynamic(d) for d in db_dynamics]
            next_offset = ""

    return BilibiliDynamicsData(dynamics=dynamics, next_offset=next_offset)
