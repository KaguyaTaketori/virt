import httpx
import math
import subprocess
import json
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.config import settings
from app.database import SessionLocal
from app.schemas.schemas import PaginatedVideosResponse, VideoResponse
from app.models.models import Video, Channel

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
CACHE_DURATION_MINUTES = 30


def _parse_duration(duration_str: Optional[str]) -> Optional[str]:
    if not duration_str:
        return None

    import re

    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    if not match:
        return None

    hours, minutes, seconds = match.groups()
    parts = []
    if hours:
        parts.append(f"{int(hours):02d}")
    if minutes:
        parts.append(f"{int(minutes):02d}")
    if seconds:
        parts.append(f"{int(seconds):02d}")
    elif not parts:
        return "00:00"

    return ":".join(parts)


def _get_status_from_broadcast(live_broadcast_content: Optional[str]) -> str:
    if live_broadcast_content == "live":
        return "live"
    elif live_broadcast_content == "upcoming":
        return "upcoming"
    else:
        return "archive"


def _parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except:
        return None


def _needs_update(channel: Channel) -> bool:
    if not channel.videos_last_fetched:
        return True
    now = datetime.now(timezone.utc)
    last_fetched = channel.videos_last_fetched
    if last_fetched.tzinfo is None:
        last_fetched = last_fetched.replace(tzinfo=timezone.utc)
    elapsed = now - last_fetched
    return elapsed > timedelta(minutes=CACHE_DURATION_MINUTES)


def _get_videos_from_db(
    db: Session, channel_id: int, page: int, page_size: int, status_filter: str = None
) -> PaginatedVideosResponse:
    query = db.query(Video).filter(Video.channel_id == channel_id)

    if status_filter == "live":
        query = query.filter(Video.status == "stream")  # 直播Tab：显示直播/录播
    elif status_filter == "upload":
        query = query.filter(Video.status == "upload")  # 视频Tab：显示自制视频
    elif status_filter == "short":
        query = query.filter(Video.status == "short")  # Shorts Tab：显示Shorts
    elif status_filter:
        query = query.filter(Video.status == status_filter)
    else:
        query = query.filter(Video.status == "upload")

    query = query.order_by(desc(Video.published_at))

    total = query.count()
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0

    offset = (page - 1) * page_size
    videos = query.offset(offset).limit(page_size).all()

    video_responses = [
        VideoResponse(
            id=v.video_id,
            title=v.title,
            thumbnail_url=v.thumbnail_url,
            duration=v.duration,
            view_count=v.view_count,
            published_at=v.published_at.isoformat() if v.published_at else None,
            status=v.status,
        )
        for v in videos
    ]

    return PaginatedVideosResponse(
        videos=video_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


async def get_channel_videos(
    channel_id: int,
    page: int = 1,
    page_size: int = 24,
    status_filter: str = None,
) -> PaginatedVideosResponse:
    """获取频道视频列表（带缓存的增量更新）"""

    db = SessionLocal()
    try:
        channel = db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return PaginatedVideosResponse(
                videos=[], total=0, page=page, page_size=page_size, total_pages=0
            )

        existing_count = db.query(Video).filter(Video.channel_id == channel_id).count()

        if _needs_update(channel):
            await _incrementally_update_videos(db, channel)

        return _get_videos_from_db(db, channel_id, page, page_size, status_filter)

    finally:
        db.close()


async def _incrementally_update_videos(db: Session, channel: Channel):
    """增量更新视频 - 只获取新视频，优先使用YouTube API，失败则用yt-dlp"""

    existing_video_ids = set(
        v[0]
        for v in db.query(Video.video_id).filter(Video.channel_id == channel.id).all()
    )

    api_quota_exceeded = False

    if settings.youtube_api_key:
        try:
            api_quota_exceeded = await _update_videos_via_api(
                db, channel, existing_video_ids
            )
        except Exception as e:
            print(f"[YouTube Videos] API error: {e}")
            api_quota_exceeded = True

    if api_quota_exceeded or not settings.youtube_api_key:
        print("[YouTube Videos] Using yt-dlp fallback...")
        try:
            await _update_videos_via_yt_dlp(db, channel, existing_video_ids)
            await _update_live_via_yt_dlp(db, channel, existing_video_ids)
            await _update_shorts_via_yt_dlp(db, channel, existing_video_ids)
        except Exception as e:
            print(f"[YouTube Videos] yt-dlp error: {e}")

    channel.videos_last_fetched = datetime.now(timezone.utc)
    db.commit()


async def _update_videos_via_api(
    db: Session, channel: Channel, existing_video_ids: set
) -> bool:
    """通过YouTube API更新视频，返回是否配额超限"""

    if not settings.youtube_api_key:
        return True

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            new_video_ids = []
            next_token = None
            max_results = 50

            while len(new_video_ids) < max_results:
                search_params = {
                    "part": "id,snippet",
                    "channelId": channel.channel_id,
                    "type": "video",
                    "order": "date",
                    "maxResults": max_results,
                    "key": settings.youtube_api_key,
                }

                if next_token:
                    search_params["pageToken"] = next_token

                resp = await client.get(
                    f"{YOUTUBE_API_BASE}/search", params=search_params
                )

                if resp.status_code == 403:
                    data = resp.json()
                    if "quotaExceeded" in str(data):
                        return True
                    return False

                if resp.status_code != 200:
                    return False

                data = resp.json()
                items = data.get("items", [])
                next_token = data.get("nextPageToken")

                for item in items:
                    video_id = item.get("id", {}).get("videoId")
                    if video_id and video_id not in existing_video_ids:
                        new_video_ids.append(item)
                    if len(new_video_ids) >= max_results:
                        break

                if not next_token:
                    break

            if not new_video_ids:
                return False

            video_id_to_status = {}
            for item in new_video_ids:
                video_id = item.get("id", {}).get("videoId")
                if video_id:
                    snippet = item.get("snippet", {})
                    live_broadcast = snippet.get("liveBroadcastContent", "none")
                    video_id_to_status[video_id] = _get_status_from_broadcast(
                        live_broadcast
                    )

            video_ids_to_fetch = list(video_id_to_status.keys())

            details_params = {
                "part": "contentDetails,statistics,snippet",
                "id": ",".join(video_ids_to_fetch),
                "key": settings.youtube_api_key,
            }

            details_resp = await client.get(
                f"{YOUTUBE_API_BASE}/videos", params=details_params
            )

            if details_resp.status_code == 200:
                details_data = details_resp.json()
                details_items = details_data.get("items", [])

                for item in details_items:
                    snippet = item.get("snippet", {})
                    content_details = item.get("contentDetails", {})
                    statistics = item.get("statistics", {})

                    video_id = item.get("id", "")
                    status = video_id_to_status.get(video_id, "archive")

                    video = Video(
                        channel_id=channel.id,
                        platform=channel.platform,
                        video_id=video_id,
                        title=snippet.get("title", ""),
                        thumbnail_url=snippet.get("thumbnails", {})
                        .get("high", {})
                        .get("url")
                        or snippet.get("thumbnails", {}).get("medium", {}).get("url"),
                        duration=_parse_duration(content_details.get("duration")),
                        view_count=int(statistics.get("viewCount", 0)),
                        published_at=_parse_datetime(snippet.get("publishedAt")),
                        status=status,
                        fetched_at=datetime.now(timezone.utc),
                    )
                    db.add(video)

                db.commit()

        return False

    except Exception as e:
        print(f"[YouTube Videos] API update error: {e}")
        return True


async def _update_videos_via_yt_dlp(
    db: Session, channel: Channel, existing_video_ids: set
):
    """通过yt-dlp更新自制视频（从videos页面）"""

    try:
        channel_url = f"https://www.youtube.com/channel/{channel.channel_id}/videos"

        result = subprocess.run(
            [
                "yt-dlp",
                "--playlist-end",
                "100",
                "--print",
                "%(id)s|%(title)s|%(duration)s|%(view_count)s|%(upload_date)s|%(thumbnail)s",
                channel_url,
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )

        if result.returncode != 0:
            print(f"[YouTube Videos] yt-dlp videos error: {result.stderr}")
            return

        for line in result.stdout.strip().split("\n"):
            if not line or "|" not in line:
                continue
            if not line[0].isalnum():
                continue

            parts = line.split("|")
            if len(parts) < 4:
                continue

            video_id = parts[0].strip()
            title = parts[1].strip() if len(parts) > 1 else ""
            duration_str = parts[2].strip() if len(parts) > 2 else ""
            view_count = parts[3].strip() if len(parts) > 3 else "0"
            upload_date = parts[4].strip() if len(parts) > 4 else ""
            thumbnail = parts[5].strip() if len(parts) > 5 else ""

            if not video_id or video_id in existing_video_ids:
                continue

            published_at = None
            if upload_date:
                try:
                    published_at = datetime.strptime(upload_date, "%Y%m%d").replace(
                        tzinfo=timezone.utc
                    )
                except:
                    pass

            duration_formatted = None
            if duration_str and duration_str != "None":
                try:
                    total_seconds = int(duration_str)
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    if hours > 0:
                        duration_formatted = f"{hours}:{minutes:02d}:{seconds:02d}"
                    else:
                        duration_formatted = f"{minutes}:{seconds:02d}"
                except:
                    pass

            video = Video(
                channel_id=channel.id,
                platform=channel.platform,
                video_id=video_id,
                title=title,
                thumbnail_url=thumbnail,
                duration=duration_formatted,
                view_count=int(view_count) if view_count.isdigit() else 0,
                published_at=published_at,
                status="upload",  # 自制视频
                fetched_at=datetime.now(timezone.utc),
            )
            db.add(video)

        db.commit()
        print(f"[YouTube Videos] yt-dlp added uploaded videos")

    except subprocess.TimeoutExpired:
        print("[YouTube Videos] yt-dlp videos timeout")
    except Exception as e:
        print(f"[YouTube Videos] yt-dlp videos error: {e}")


async def _update_live_via_yt_dlp(
    db: Session, channel: Channel, existing_video_ids: set
):
    """通过yt-dlp获取直播/预约视频"""

    try:
        streams_url = f"https://www.youtube.com/channel/{channel.channel_id}/streams"

        result = subprocess.run(
            [
                "yt-dlp",
                "--playlist-end",
                "10",
                "--print",
                "%(id)s|%(title)s|%(duration)s|%(view_count)s|%(upload_date)s|%(thumbnail)s",
                streams_url,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            return

        for line in result.stdout.strip().split("\n"):
            if not line or "|" not in line:
                continue
            if not line[0].isalnum():
                continue

            parts = line.split("|")
            if len(parts) < 4:
                continue

            video_id = parts[0].strip()
            title = parts[1].strip() if len(parts) > 1 else ""
            duration_str = parts[2].strip() if len(parts) > 2 else ""
            view_count = parts[3].strip() if len(parts) > 3 else "0"
            upload_date = parts[4].strip() if len(parts) > 4 else ""
            thumbnail = parts[5].strip() if len(parts) > 5 else ""

            if not video_id or video_id in existing_video_ids:
                continue

            published_at = None
            if upload_date:
                try:
                    published_at = datetime.strptime(upload_date, "%Y%m%d").replace(
                        tzinfo=timezone.utc
                    )
                except:
                    pass

            status = "live"
            duration_formatted = None
            if duration_str and duration_str != "None":
                try:
                    total_seconds = int(duration_str)
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    if hours > 0:
                        duration_formatted = f"{hours}:{minutes:02d}:{seconds:02d}"
                    else:
                        duration_formatted = f"{minutes}:{seconds:02d}"
                    if total_seconds > 0:
                        status = "archive"
                except:
                    pass

            video = Video(
                channel_id=channel.id,
                platform=channel.platform,
                video_id=video_id,
                title=title,
                thumbnail_url=thumbnail,
                duration=duration_formatted,
                view_count=int(view_count) if view_count.isdigit() else 0,
                published_at=published_at,
                status="stream",  # 直播/录播
                fetched_at=datetime.now(timezone.utc),
            )
            db.add(video)

        db.commit()
        print(f"[YouTube Videos] yt-dlp added live streams")

    except subprocess.TimeoutExpired:
        print("[YouTube Videos] yt-dlp streams timeout")
    except Exception as e:
        print(f"[YouTube Videos] yt-dlp streams error: {e}")


async def _update_shorts_via_yt_dlp(
    db: Session, channel: Channel, existing_video_ids: set
):
    """通过yt-dlp获取Shorts视频"""

    try:
        shorts_url = f"https://www.youtube.com/channel/{channel.channel_id}/shorts"

        result = subprocess.run(
            [
                "yt-dlp",
                "--playlist-end",
                "100",
                "--print",
                "%(id)s|%(title)s|%(duration)s|%(view_count)s|%(upload_date)s|%(thumbnail)s",
                shorts_url,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            return

        for line in result.stdout.strip().split("\n"):
            if not line or "|" not in line:
                continue
            if not line[0].isalnum():
                continue

            parts = line.split("|")
            if len(parts) < 4:
                continue

            video_id = parts[0].strip()
            title = parts[1].strip() if len(parts) > 1 else ""
            duration_str = parts[2].strip() if len(parts) > 2 else ""
            view_count = parts[3].strip() if len(parts) > 3 else "0"
            upload_date = parts[4].strip() if len(parts) > 4 else ""
            thumbnail = parts[5].strip() if len(parts) > 5 else ""

            if not video_id or video_id in existing_video_ids:
                continue

            published_at = None
            if upload_date:
                try:
                    published_at = datetime.strptime(upload_date, "%Y%m%d").replace(
                        tzinfo=timezone.utc
                    )
                except:
                    pass

            duration_formatted = None
            if duration_str and duration_str != "None":
                try:
                    total_seconds = int(duration_str)
                    minutes = total_seconds // 60
                    seconds = total_seconds % 60
                    duration_formatted = f"{minutes}:{seconds:02d}"
                except:
                    pass

            video = Video(
                channel_id=channel.id,
                platform=channel.platform,
                video_id=video_id,
                title=title,
                thumbnail_url=thumbnail,
                duration=duration_formatted,
                view_count=int(view_count) if view_count.isdigit() else 0,
                published_at=published_at,
                status="short",  # Shorts
                fetched_at=datetime.now(timezone.utc),
            )
            db.add(video)

        db.commit()
        print(f"[YouTube Videos] yt-dlp added shorts")

    except subprocess.TimeoutExpired:
        print("[YouTube Videos] yt-dlp shorts timeout")
    except Exception as e:
        print(f"[YouTube Videos] yt-dlp shorts error: {e}")


async def _full_refresh_videos(db: Session, channel: Channel):
    """全量刷新视频 - 删除旧数据重新获取"""

    if not settings.youtube_api_key:
        return

    try:
        db.query(Video).filter(Video.channel_id == channel.id).delete()
        db.commit()

        all_video_ids = []
        total_results = 0
        next_token = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            while len(all_video_ids) < 500:
                search_params = {
                    "part": "id,snippet",
                    "channelId": channel.channel_id,
                    "type": "video",
                    "order": "date",
                    "maxResults": 50,
                    "key": settings.youtube_api_key,
                }

                if next_token:
                    search_params["pageToken"] = next_token

                resp = await client.get(
                    f"{YOUTUBE_API_BASE}/search", params=search_params
                )

                if resp.status_code != 200:
                    break

                data = resp.json()
                items = data.get("items", [])
                next_token = data.get("nextPageToken")
                page_info = data.get("pageInfo", {})

                if total_results == 0:
                    total_results = page_info.get("totalResults", 0)

                for item in items:
                    video_id = item.get("id", {}).get("videoId")
                    if video_id:
                        all_video_ids.append(item)

                if not next_token:
                    break

            if not all_video_ids:
                return

            video_id_to_status = {}
            for item in all_video_ids:
                video_id = item.get("id", {}).get("videoId")
                if video_id:
                    snippet = item.get("snippet", {})
                    live_broadcast = snippet.get("liveBroadcastContent", "none")
                    video_id_to_status[video_id] = _get_status_from_broadcast(
                        live_broadcast
                    )

            video_ids_to_fetch = list(video_id_to_status.keys())

            for i in range(0, len(video_ids_to_fetch), 50):
                batch_ids = video_ids_to_fetch[i : i + 50]

                details_params = {
                    "part": "contentDetails,statistics,snippet",
                    "id": ",".join(batch_ids),
                    "key": settings.youtube_api_key,
                }

                details_resp = await client.get(
                    f"{YOUTUBE_API_BASE}/videos", params=details_params
                )

                if details_resp.status_code == 200:
                    details_data = details_resp.json()
                    details_items = details_data.get("items", [])

                    for item in details_items:
                        snippet = item.get("snippet", {})
                        content_details = item.get("contentDetails", {})
                        statistics = item.get("statistics", {})

                        video_id = item.get("id", "")
                        status = video_id_to_status.get(video_id, "archive")

                        video = Video(
                            channel_id=channel.id,
                            platform=channel.platform,
                            video_id=video_id,
                            title=snippet.get("title", ""),
                            thumbnail_url=snippet.get("thumbnails", {})
                            .get("high", {})
                            .get("url")
                            or snippet.get("thumbnails", {})
                            .get("medium", {})
                            .get("url"),
                            duration=_parse_duration(content_details.get("duration")),
                            view_count=int(statistics.get("viewCount", 0)),
                            published_at=_parse_datetime(snippet.get("publishedAt")),
                            status=status,
                            fetched_at=datetime.now(timezone.utc),
                        )
                        db.add(video)

            db.commit()

        channel.videos_last_fetched = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        print(f"[YouTube Videos] Full refresh error: {e}")
