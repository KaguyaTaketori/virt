# backend/app/services/bilibili_fetcher.py
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from typing import Optional
import httpx

BILIBILI_LIVE_API = "https://api.live.bilibili.com"
BILIBILI_API = "https://api.bilibili.com"

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://live.bilibili.com/",
    "Origin": "https://live.bilibili.com",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept": "application/json, text/plain, */*",
    "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24"',
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-site": "same-site",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
}

_BACKOFF_INIT = 60
_BACKOFF_MAX = 600
_BACKOFF_FACTOR = 2
_MAX_RETRIES = 3
_BATCH_SIZE = 15  # 每批最多 15 个 uid
_BATCH_SLEEP = (3.0, 5.0)  # 批次间随机冷却秒数
_REQ_SLEEP = (1.0, 2.2)  # 单请求间随机间隔


async def get_user_videos(
    client: httpx.AsyncClient, uid: str, pn: int = 1, ps: int = 30
) -> Optional[dict]:
    """
    获取用户的视频投稿列表
    需要延迟避免风控，pn=页码，ps=每页数量
    """
    backoff = 3.0
    for attempt in range(3):
        await asyncio.sleep(backoff)
        try:
            resp = await client.get(
                f"{BILIBILI_API}/x/space/arc/search",
                params={"mid": uid, "pn": pn, "ps": ps},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                    "Referer": "https://space.bilibili.com/",
                },
                timeout=15.0,
            )
            if resp.status_code == 412:
                print(f"[Bilibili] get_user_videos 412, backoff {backoff}s uid={uid}")
                backoff = min(backoff * 2, 60)
                continue
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                print(f"[Bilibili] get_user_videos code={data.get('code')} uid={uid}")
                return None
            return data.get("data", {})
        except Exception as e:
            print(f"[Bilibili] get_user_videos uid={uid} error: {e}")
            backoff = min(backoff * 2, 60)
    return None


async def sync_bilibili_channel_videos(db, channel_id: int, channel_id_str: str) -> int:
    """同步bilibili频道视频到数据库"""
    import asyncio

    async with httpx.AsyncClient(timeout=30.0) as client:
        total_synced = 0
        page = 1
        page_size = 30

        while True:
            data = await get_user_videos(client, channel_id_str, page, page_size)
            if not data:
                break

            vlist = data.get("list", {}).get("vlist", [])
            if not vlist:
                break

            for v in vlist:
                bvid = v.get("bvid", "")
                if not bvid:
                    continue

                from app.models.models import Video, Platform
                from datetime import datetime

                existing = (
                    db.query(Video)
                    .filter(Video.channel_id == channel_id, Video.video_id == bvid)
                    .first()
                )

                published = None
                if v.get("created"):
                    try:
                        published = datetime.fromtimestamp(v.get("created"))
                    except:
                        pass

                if existing:
                    existing.title = v.get("title")
                    existing.thumbnail_url = v.get("pic", "")
                    existing.view_count = v.get("play", 0)
                    existing.duration = v.get("length", "")
                    existing.published_at = published
                else:
                    video = Video(
                        channel_id=channel_id,
                        platform=Platform.BILIBILI,
                        video_id=bvid,
                        title=v.get("title", ""),
                        thumbnail_url=v.get("pic", ""),
                        duration=v.get("length", ""),
                        view_count=v.get("play", 0),
                        published_at=published,
                        status="archive",
                    )
                    db.add(video)
                total_synced += 1

            db.commit()

            page_info = data.get("page", {})
            count = page_info.get("count", 0)
            if page * page_size >= count:
                break
            page += 1
            await asyncio.sleep(2)

        return total_synced


async def get_user_info(client: httpx.AsyncClient, uid: str) -> Optional[dict]:
    await asyncio.sleep(random.uniform(0.8, 1.8))
    try:
        resp = await client.get(
            f"{BILIBILI_API}/x/web-interface/card",
            params={"mid": uid, "photo": "true"},
            headers=BASE_HEADERS,
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            return None
        card = data.get("data", {}).get("card", {})
        return {
            "name": card.get("name"),
            "avatar_url": card.get("face"),
            "sex": card.get("sex"),
            "sign": card.get("sign"),
            "fans": card.get("fans"),
            "attention": card.get("attention"),
            "archive_count": data.get("archive_count"),
            "article_count": data.get("article_count"),
            "follower": data.get("follower"),
            "like_num": data.get("like_num"),
            "level": card.get("level_info", {}).get("current_level"),
            "official_title": card.get("Official", {}).get("title"),
            "official_type": card.get("Official", {}).get("type"),
            "vip_type": card.get("vip", {}).get("type"),
            "vip_status": card.get("vip", {}).get("status"),
        }
    except Exception as e:
        print(f"[Bilibili] get_user_info uid={uid} error: {e}")
        return None


async def _fetch_single_room(
    client: httpx.AsyncClient,
    uid: str,
    current_backoff: list,  # 用 list 包裹以便跨 await 修改
) -> Optional[dict]:
    """
    拉单个 uid 的直播间信息，带退避重试。
    current_backoff 是 [value] 形式，退避时间在所有 uid 间共享。
    """
    for attempt in range(_MAX_RETRIES):
        try:
            resp = await client.get(
                f"{BILIBILI_LIVE_API}/room/v1/Room/getRoomInfoOld",
                params={"mid": uid},
                headers=BASE_HEADERS,
                timeout=15.0,
            )
        except httpx.TimeoutException:
            print(f"[Bilibili] 超时 uid={uid} attempt={attempt + 1}")
            await asyncio.sleep(5)
            continue
        except httpx.RequestError as e:
            print(f"[Bilibili] 网络错误 uid={uid}: {e}")
            return None

        if resp.status_code == 412:
            wait = current_backoff[0]
            print(
                f"[Bilibili] 风控 412 uid={uid}，退避 {wait}s (attempt {attempt + 1})"
            )
            await asyncio.sleep(wait)
            current_backoff[0] = min(wait * _BACKOFF_FACTOR, _BACKOFF_MAX)
            continue

        if resp.status_code != 200:
            print(f"[Bilibili] 非预期状态 {resp.status_code} uid={uid}")
            return None

        try:
            data = resp.json()
        except Exception:
            print(f"[Bilibili] JSON 解析失败 uid={uid}")
            return None

        if data.get("code") == 0:
            room = data.get("data", {})
            if room:
                # 成功后重置退避
                current_backoff[0] = _BACKOFF_INIT
                return {
                    "room_id": room.get("roomid"),
                    "title": room.get("title"),
                    "user_cover": room.get("cover"),
                    "live_status": room.get("liveStatus"),
                    "online": room.get("online"),
                    "live_time": room.get("live_time"),
                }

        current_backoff[0] = _BACKOFF_INIT
        return None  # code != 0，认为该 uid 无直播间

    print(f"[Bilibili] uid={uid} 重试耗尽，跳过")
    return None


async def get_rooms_by_uids(
    client: httpx.AsyncClient,
    uids: list[str],
) -> dict:
    """
    分批串行拉直播状态，批次内顺序请求，批次间随机冷却。
    返回 {uid_str: room_data_dict}。
    """
    results: dict[str, dict] = {}
    backoff = [_BACKOFF_INIT]  # 共享退避状态

    batches = [uids[i : i + _BATCH_SIZE] for i in range(0, len(uids), _BATCH_SIZE)]
    print(f"[Bilibili] 共 {len(uids)} 个 uid，分 {len(batches)} 批处理")

    for batch_idx, batch in enumerate(batches):
        for uid in batch:
            await asyncio.sleep(random.uniform(*_REQ_SLEEP))
            room = await _fetch_single_room(client, uid, backoff)
            if room:
                results[str(uid)] = room

        # 批次间冷却（最后一批不用等）
        if batch_idx < len(batches) - 1:
            sleep_time = random.uniform(*_BATCH_SLEEP)
            print(
                f"[Bilibili] 批次 {batch_idx + 1}/{len(batches)} 完成，冷却 {sleep_time:.1f}s"
            )
            await asyncio.sleep(sleep_time)

    return results


def parse_bilibili_room(room: dict) -> dict:
    live_status = room.get("live_status", 0)
    status_map = {0: "offline", 1: "live", 2: "upcoming"}

    started_at = None
    live_time = room.get("live_time")
    if live_time and live_status == 1:
        try:
            started_at = datetime.fromtimestamp(int(live_time), tz=timezone.utc)
        except (ValueError, OSError, TypeError):
            pass

    return {
        "video_id": str(room.get("room_id", "")),
        "title": room.get("title"),
        "thumbnail_url": room.get("user_cover") or room.get("keyframe"),
        "status": status_map.get(live_status, "offline"),
        "viewer_count": room.get("online", 0),
        "started_at": started_at,
    }
