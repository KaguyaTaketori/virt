from dataclasses import dataclass
from typing import Optional
from bilibili_api import Credential
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Channel, User
from app.integrations.bili_client import BiliClient

@dataclass
class BilibiliChannelData:
    info: Optional[dict]
    dynamics: list
    videos: list
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


async def fetch_bilibili_channel_data(
    db: AsyncSession,
    channel: Channel,
    credential: Optional[Credential],
    client: BiliClient,
    dynamics_offset: str = "",
    dynamics_limit: int = 12,
) -> BilibiliChannelData:
    """聚合B站频道数据，封装所有fallback逻辑。"""
    uid = channel.channel_id

    # 视频
    videos = []
    try:
        raw = await client.get_videos(uid, credential=credential, page=1, page_size=30)
        videos = [client._parse_video(v) for v in raw.get("list", {}).get("vlist", [])]
    except Exception:
        pass

    # 动态 (API → DB fallback)
    dynamics, next_offset = [], ""
    if credential:
        try:
            dynamics, next_offset = await client.get_dynamics(
                uid, offset=dynamics_offset, credential=credential
            )
            if dynamics:
                await client.upsert_dynamics(db, channel.id, dynamics, [])
        except Exception:
            pass

    # if not dynamics:
    #     from app.models.models import BilibiliDynamic
    #     from sqlalchemy import select
    #     result = await db.execute(
    #         select(BilibiliDynamic)
    #         .where(BilibiliDynamic.channel_id == channel.id)
    #         .order_by(BilibiliDynamic.timestamp.desc())
    #         .limit(dynamics_limit)
    #     )
    #     dynamics = [_row_to_dict(row) for row in result.scalars().all()]

    info_obj = await client.get_channel_info(uid, credential)
    if info_obj:
        channel.name = info_obj.name or channel.name
        channel.bilibili_face = info_obj.face or channel.bilibili_face
        channel.bilibili_sign = info_obj.sign or channel.bilibili_sign
        channel.bilibili_fans = info_obj.fans or channel.bilibili_fans
        channel.bilibili_archive_count = info_obj.archive_count or channel.bilibili_archive_count
        await db.commit()

    info_dict = {
        "mid": uid, "name": channel.name,
        "face": channel.bilibili_face, "sign": channel.bilibili_sign,
        "fans": channel.bilibili_fans, "attention": channel.bilibili_following,
        "archive_count": channel.bilibili_archive_count,
    }
    return BilibiliChannelData(info=info_dict, dynamics=dynamics,
                                videos=videos, next_offset=next_offset)