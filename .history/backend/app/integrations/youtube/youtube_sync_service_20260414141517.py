import asyncio
import random
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict, FrozenSet

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import upsert
from app.loguru_config import logger
from app.models.models import Channel, Video, Platform
from app.schemas.schemas import YTLiveStatus
from app.core.exceptions import YouTubeAPIError

from .youtube_api_client import YouTubeApiClient
from .video_parser import VideoParser

_column_cache_lock = asyncio.Lock()
_column_cache: dict[str, FrozenSet[str]] = {}


class YouTubeSyncService:
    """
    YouTube 同步服务：业务逻辑的核心。
    协调 API 请求、解析响应，并执行数据库写入。
    """

    def __init__(self, api_client: YouTubeApiClient, parser: VideoParser):
        self.api = api_client
        self.parser = parser

    @property
    def platform(self) -> Platform:
        return Platform.YOUTUBE

    async def _get_table_columns(self, model_class) -> FrozenSet[str]:
        """获取并缓存数据库模型的列名"""
        table_name = model_class.__tablename__
        if table_name not in _column_cache:
            async with _column_cache_lock:
                if table_name not in _column_cache:
                    cols = frozenset(
                        c.key for c in inspect(model_class).mapper.column_attrs
                    )
                    _column_cache[table_name] = cols
        return _column_cache[table_name]

    def _uc_to_uu(self, channel_id: str) -> Optional[str]:
        """将频道 ID (UC...) 转换为上传列表 ID (UU...)"""
        if channel_id and channel_id.startswith("UC"):
            return "UU" + channel_id[2:]
        return None

    async def resolve_channel_id(self, input_str: str) -> Optional[str]:
        """从各种输入形式（URL、Handle、ID）解析出标准的 UC ID"""
        if not input_str:
            return None

        input_str = input_str.strip()
        # 已经是标准 ID
        if input_str.startswith("UC") and len(input_str) >= 22:
            return input_str

        # 构建安全 URL
        safe_url = None
        if input_str.startswith("@"):
            handle = input_str.lstrip("@")
            if handle.replace("-", "").replace("_", "").replace(".", "").isalnum():
                safe_url = f"https://www.youtube.com/@{handle}"
        elif input_str.startswith("http"):
            safe_url = input_str
        else:
            safe_slug = "".join(c for c in input_str if c.isalnum() or c in "-_.")
            if safe_slug:
                safe_url = f"https://www.youtube.com/@{safe_slug}"

        if not safe_url:
            return None

        return await self.api.resolve_from_url(safe_url)

    async def get_channel_info(self, channel_id: str) -> Optional[dict]:
        """获取频道信息，优先 API，失败则 Fallback 爬虫"""
        if not channel_id or not channel_id.startswith("UC"):
            return None

        # 尝试 API
        try:
            raw_item = await self.api.get_channel_info_api(channel_id)
            if raw_item:
                return self.parser.parse_channel_api_response(raw_item, channel_id)
        except Exception as e:
            logger.warning("YouTube API Error for channel info: {}", e)

        # 尝试爬虫 Fallback
        html_text = await self.api.get_channel_info_fallback(channel_id)
        if html_text:
            return self.parser.parse_channel_html(html_text, channel_id)

        return None

    async def get_live_status(self, channel_id: str) -> YTLiveStatus:
        """获取单个频道的直播状态"""
        try:
            item = await self.api.get_live_search_result(channel_id)
            if item:
                snippet = item.get("snippet", {})
                return YTLiveStatus(
                    video_id=item.get("id", {}).get("videoId"),
                    title=snippet.get("title"),
                    thumbnail_url=snippet.get("thumbnails", {})
                    .get("high", {})
                    .get("url"),
                    status="live",
                    viewer_count=0,
                    started_at=self.parser.parse_datetime(snippet.get("publishedAt")),
                )
        except YouTubeAPIError as e:
            raise e
        except Exception as e:
            raise YouTubeAPIError(f"获取直播状态失败: {e}", original_error=e)

        return YTLiveStatus(status="offline")

    async def batch_get_live_status(
        self, channel_ids: List[str], max_concurrent: int = 5
    ) -> Dict[str, YTLiveStatus]:
        """批量获取多个频道的直播状态"""
        semaphore = asyncio.Semaphore(max_concurrent)
        results: Dict[str, YTLiveStatus] = {}

        async def fetch_with_limit(cid: str):
            async with semaphore:
                await asyncio.sleep(random.uniform(0.5, 1.5))
                try:
                    status = await self.get_live_status(cid)
                    return cid, status
                except Exception:
                    return cid, YTLiveStatus(status="offline")

        tasks = [fetch_with_limit(cid) for cid in channel_ids]
        completed = await asyncio.gather(*tasks)

        for cid, status in completed:
            results[cid] = status

        return results

    async def _upsert_video(self, session: AsyncSession, video_data: dict) -> None:
        """执行具体的数据库 Upsert 动作"""
        db_columns = await self._get_table_columns(Video)

        # 只保留模型中存在的字段
        safe_data = {k: v for k, v in video_data.items() if k in db_columns}
        safe_data["fetched_at"] = datetime.now(timezone.utc)

        # 定义需要更新的列
        update_cols = {
            k: v
            for k, v in safe_data.items()
            if k not in ["id", "channel_id", "video_id", "platform"]
        }

        await upsert(
            session,
            Video,
            values=safe_data,
            index_elements=["channel_id", "video_id"],
            update_cols=update_cols,
        )

    async def sync_channel_videos(
        self,
        session: AsyncSession,
        channel: Channel,
        full_refresh: bool = False,
        progress: Any = None,
        task_id: Any = None,
    ) -> int:
        """
        同步频道视频的主逻辑。
        1. 确定 Playlist ID。
        2. 循环翻页获取视频 ID。
        3. 批量获取视频详情。
        4. 解析并 Upsert 数据库。
        """
        total_processed = 0
        page_token: Optional[str] = None
        playlist_id = self._uc_to_uu(channel.channel_id)

        while True:
            video_ids, next_token, status = await self.api.fetch_playlist_page(
                playlist_id, page_token
            )

            # 如果 UU ID 报错，尝试 API 获取真实 Uploads Playlist ID
            if status != 200 and page_token is None:
                logger.info("UU ID {} 校验失败，尝试获取真实 Uploads ID", playlist_id)
                playlist_id = await self.api.get_real_uploads_playlist_id(
                    channel.channel_id
                )
                if not playlist_id:
                    break
                video_ids, next_token, status = await self.api.fetch_playlist_page(
                    playlist_id
                )

            if not video_ids:
                break

            # 批量获取详情（YouTube 详情接口支持一次 50 个 ID）
            items = await self.api.fetch_video_details_batch(video_ids)
            for item in items:
                video_data = self.parser.parse_video_item(
                    channel.id, channel.platform.value, item
                )
                await self._upsert_video(session, video_data)
                total_processed += 1
                if progress and task_id:
                    progress.update(
                        task_id, 
                        advance=1, 
                        description=f"正在抓取 [bold cyan]{channel.name[:10]}[/bold cyan] (已获 {total_processed} 视频)"
                    )

            await session.flush()

            # 如果不是全量刷新，第一页结束后就退出
            if not full_refresh or not next_token:
                break
            page_token = next_token

        channel.videos_last_fetched = datetime.now(timezone.utc)
        await session.commit()
        return total_processed

    async def fetch_and_upsert_single_video(
        self, session: AsyncSession, channel: Channel, video_id: str
    ) -> Optional[dict]:
        """同步并更新单个特定视频"""
        items = await self.api.fetch_video_details_batch([video_id])
        if not items:
            return None

        video_data = self.parser.parse_video_item(
            channel.id, channel.platform.value, items[0]
        )
        await self._upsert_video(session, video_data)
        await session.commit()
        return video_data

    async def is_channel_full_sync_completed(
        self, session: AsyncSession, channel: Channel
    ) -> bool:
        """检查数据库中的视频数量是否已达到该频道在 YouTube 上的总视频数"""
        playlist_id = self._uc_to_uu(channel.channel_id)
        if not playlist_id:
            playlist_id = await self.api.get_real_uploads_playlist_id(
                channel.channel_id
            )

        if not playlist_id:
            return False

        total_on_yt = await self.api.get_playlist_total_count(playlist_id)
        if total_on_yt is None:
            return False

        result = await session.execute(
            select(Video).where(Video.channel_id == channel.id)
        )
        db_count = len(result.scalars().all())
        return db_count >= total_on_yt
