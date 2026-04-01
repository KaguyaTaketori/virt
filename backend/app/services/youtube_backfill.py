import httpx
from app.loguru_config import logger
import re
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, Tuple

from app.config import settings
from app.models.models import Video, Channel

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def _convert_to_uploads_playlist(channel_id: str) -> str | None:
    """【核心魔法1】：将普通频道ID (UCxxx) 转换为上传播放列表ID (UUxxx)"""
    if channel_id and channel_id.startswith("UC"):
        return "UU" + channel_id[2:]
    return None


def _parse_yt_duration(duration_str: str) -> Tuple[Optional[str], int]:
    """解析 YouTube 持续时间 (PT#H#M#S)，返回 (格式化字符串, 总秒数)"""
    if not duration_str:
        return None, 0

    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    if not match:
        return None, 0

    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0

    total_seconds = hours * 3600 + minutes * 60 + seconds

    parts = []
    if hours > 0:
        parts.append(f"{hours:02d}")
    parts.append(f"{minutes:02d}")
    parts.append(f"{seconds:02d}")

    return ":".join(parts), total_seconds


def _parse_yt_datetime(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return None


def _determine_video_status(item: dict, total_seconds: int) -> str:
    """【核心逻辑】：精准判断视频类型 (直播/录播/待机/普通/Shorts)"""
    live_details = item.get("liveStreamingDetails")

    # 如果存在 liveStreamingDetails，说明是直播相关
    if live_details:
        if "actualEndTime" in live_details:
            return "archive"  # 已经播完的录播
        elif "actualStartTime" in live_details:
            return "live"  # 正在直播中
        elif "scheduledStartTime" in live_details:
            return "upcoming"  # 待机室

    # 如果不是直播，根据时长判断是否为 Shorts (粗略估计：<=60秒)
    if total_seconds > 0 and total_seconds <= 61:
        return "short"

    return "upload"  # 常规上传视频


async def backfill_channel_videos(
    db: Session, channel: Channel, full_refresh: bool = False
) -> int:
    """
    【高阶函数】：低消耗、高速度拉取频道历史视频
    - full_refresh=True: 拉取该频道历史所有视频（Initial Backfill）
    - full_refresh=False: 仅增量更新最近的 50-100 个视频

    返回: 成功处理的视频数量
    """
    if not settings.youtube_api_key:
        logger.warning("缺少 YouTube API Key")
        return 0

    uploads_playlist_id = _convert_to_uploads_playlist(channel.channel_id)
    if not uploads_playlist_id:
        logger.warning("无法转换频道ID为播放列表: {}", channel.channel_id)
        return 0

    total_processed = 0
    next_page_token = None

    # 获取数据库中该频道所有现存的 video_id，用于快速判断 Upsert (跨数据库兼容性最好)
    existing_videos_map = {
        v.video_id: v
        for v in db.query(Video).filter(Video.channel_id == channel.id).all()
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            # 1. 极低消耗：通过 PlaylistItems 获取基础列表（耗费 1 Quota / 50 视频）
            pl_params = {
                "part": "snippet",
                "playlistId": uploads_playlist_id,
                "maxResults": 50,
                "key": settings.youtube_api_key,
            }
            if next_page_token:
                pl_params["pageToken"] = next_page_token

            pl_resp = await client.get(
                f"{YOUTUBE_API_BASE}/playlistItems", params=pl_params
            )

            if pl_resp.status_code != 200:
                logger.error("获取播放列表失败: {}", pl_resp.text)
                break

            pl_data = pl_resp.json()
            items = pl_data.get("items", [])
            if not items:
                break

            # 提取这 50 个视频的 ID
            video_ids = [
                item.get("snippet", {}).get("resourceId", {}).get("videoId")
                for item in items
                if item.get("snippet", {}).get("resourceId", {}).get("videoId")
            ]

            if not video_ids:
                break

            # 2. 批量查详情：获取时长、播放量和直播状态（耗费 1 Quota / 50 视频）
            vid_resp = await client.get(
                f"{YOUTUBE_API_BASE}/videos",
                params={
                    "part": "snippet,contentDetails,statistics,liveStreamingDetails",
                    "id": ",".join(video_ids),
                    "key": settings.youtube_api_key,
                },
            )

            if vid_resp.status_code == 200:
                vid_data = vid_resp.json()
                vid_items = vid_data.get("items", [])

                # 3. 内存清洗与入库 (Upsert 逻辑，完美兼容 SQLite 与 PostgreSQL)
                for item in vid_items:
                    vid_id = item["id"]
                    snippet = item.get("snippet", {})
                    content_details = item.get("contentDetails", {})
                    statistics = item.get("statistics", {})

                    # 解析封面
                    thumbnails = snippet.get("thumbnails", {})
                    thumb_url = (
                        thumbnails.get("maxres", {}).get("url")
                        or thumbnails.get("high", {}).get("url")
                        or thumbnails.get("medium", {}).get("url")
                        or thumbnails.get("default", {}).get("url")
                    )

                    # 解析时长与状态
                    duration_str, total_seconds = _parse_yt_duration(
                        content_details.get("duration")
                    )
                    status = _determine_video_status(item, total_seconds)

                    # 组装数据
                    video_data = {
                        "title": snippet.get("title", ""),
                        "thumbnail_url": thumb_url,
                        "duration": duration_str,
                        "view_count": int(statistics.get("viewCount", 0)),
                        "published_at": _parse_yt_datetime(snippet.get("publishedAt")),
                        "status": status,
                        "fetched_at": datetime.now(timezone.utc),
                    }

                    # 执行 Insert 或 Update
                    if vid_id in existing_videos_map:
                        # 存在则更新最新状态（播放量、封面、是否从直播转为录播等）
                        existing_video = existing_videos_map[vid_id]
                        for key, value in video_data.items():
                            setattr(existing_video, key, value)
                    else:
                        # 不存在则插入
                        new_video = Video(
                            channel_id=channel.id,
                            platform=channel.platform,
                            video_id=vid_id,
                            **video_data,
                        )
                        db.add(new_video)
                        existing_videos_map[vid_id] = (
                            new_video  # 加入字典防止这一批次内重复
                        )

                # 提交这一批次（50条）到数据库
                db.commit()
                total_processed += len(vid_items)

            # 4. 翻页与增量控制逻辑
            next_page_token = pl_data.get("nextPageToken")

            # 如果不是全量拉取 (Initial Backfill)，那么拉满 50 条最近数据就可以停了
            # 因为最近的50条已经足够覆盖日常的增量更新
            if not full_refresh:
                break

            if not next_page_token:
                break

    # 更新频道最后获取时间
    channel.videos_last_fetched = datetime.now(timezone.utc)
    db.commit()

    logger.info(
        "频道 {} 视频拉取完成，共处理 {} 个视频。", channel.name, total_processed
    )
    return total_processed
