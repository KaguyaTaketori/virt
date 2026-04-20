import re
import html
from datetime import datetime
from typing import Optional, Tuple
from app.models.models import Platform
from app.constants import (
    YT_SHORT_MAX_SECS,
    YT_PREMIERE_SHORT,
    YT_PREMIERE_MEDIUM,
    YT_PREMIERE_LONG,
    YT_LIVE_THRESHOLD,
    YT_LIVE_STRONG,
    PREMIERE_POSITIVE_THRESHOLD,
)

# --- 启发式解析正则 ---
PREMIERE_TITLE_KWS = re.compile(
    r"\b(mv|official video|cover|premiere|trailer|teaser|lyric video)\b|翻唱|首播|原创|动画",
    re.IGNORECASE,
)
LIVE_TITLE_KWS = re.compile(
    r"\b(live|stream|chat|freechat)\b|🔴|直播|歌枠|杂谈|vtuber|耐久|アーカイブ",
    re.IGNORECASE,
)
PREMIERE_DESC_KWS = re.compile(
    r"\b(vocal|mix|illust|movie|director|music|arrangement)\s*[:：]", re.IGNORECASE
)
LIVE_DESC_KWS = re.compile(
    r"\b(superchat|rules|streamlabs)\b|直播规则|聊天室规则|ルール", re.IGNORECASE
)

class VideoParser:
    """
    负责将 YouTube API 的原始数据解析为应用内部格式。
    包含：时间解析、时长计算、视频状态启发式判定。
    """

    def clean_youtube_url(self, extracted_url: str) -> str:
        """清洗 URL 中的转义字符"""
        if not extracted_url:
            return extracted_url
        return extracted_url.replace("\\u0026", "&").replace("\\/", "/")

    def parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """解析 ISO 8601 时间字符串"""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except Exception:
            return None

    def parse_duration(self, iso_duration: Optional[str]) -> Tuple[Optional[str], int]:
        """将 ISO 8601 时长转换为 (格式化字符串, 总秒数)"""
        if not iso_duration:
            return None, 0

        match = re.fullmatch(
            r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration
        )
        if not match:
            return None, 0

        days = int(match.group(1) or 0)
        hours = int(match.group(2) or 0) + days * 24
        minutes = int(match.group(3) or 0)
        seconds = int(match.group(4) or 0)

        total_secs = hours * 3600 + minutes * 60 + seconds

        if hours > 0:
            fmt = f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            fmt = f"{minutes}:{seconds:02d}"

        return fmt, total_secs

    def is_premiere_heuristic(self, item: dict, total_secs: int) -> bool:
        """
        基于标题、描述、时长和分类的启发式算法：
        判断一个已结束的直播归档是否实际上是一个“首播(Premiere)”视频（如 MV）。
        """
        score = 0
        snippet = item.get("snippet", {})
        title = snippet.get("title", "")
        description = snippet.get("description", "")
        category_id = snippet.get("categoryId", "")

        # 1. 基于时长的评分
        if total_secs < YT_PREMIERE_SHORT:
            score += 80
        elif total_secs < YT_PREMIERE_MEDIUM:
            score += 40
        elif total_secs < YT_PREMIERE_LONG:
            score += 20
        elif total_secs > YT_LIVE_STRONG:
            score -= 80
        elif total_secs > YT_LIVE_THRESHOLD:
            score -= 40

        # 2. 基于标题关键字
        if PREMIERE_TITLE_KWS.search(title):
            score += 30
        if LIVE_TITLE_KWS.search(title):
            score -= 40

        # 3. 基于描述关键字 (首播通常有制作人员名单)
        if PREMIERE_DESC_KWS.search(description):
            score += 30
        if LIVE_DESC_KWS.search(description):
            score -= 40

        # 4. 基于分类 (10=Music, 20=Gaming)
        if category_id == "10":
            score += 20
        elif category_id == "20":
            score -= 15

        return score > PREMIERE_POSITIVE_THRESHOLD

    def determine_video_status(self, item: dict, total_secs: int) -> str:
        """判定视频当前状态: live, upcoming, archive, short, upload"""
        snippet = item.get("snippet", {})
        live_content = snippet.get("liveBroadcastContent", "none")
        live_details = item.get("liveStreamingDetails", {})

        if live_content == "live":
            return "live"
        if live_content == "upcoming":
            return "upcoming"

        # 如果有实际结束时间，说明是直播归档或首播
        if live_details.get("actualEndTime"):
            is_premiere = self.is_premiere_heuristic(item, total_secs)
            return "upload" if is_premiere else "archive"

        # 短视频判定
        if 0 < total_secs <= YT_SHORT_MAX_SECS:
            return "short"

        return "upload"

    def extract_thumbnail(self, snippet: dict) -> Optional[str]:
        """获取最高质量的缩略图 URL"""
        thumbs = snippet.get("thumbnails", {})
        for quality in ("maxres", "standard", "high", "medium", "default"):
            url = thumbs.get(quality, {}).get("url")
            if url:
                return url
        return None

    def parse_video_item(
        self, channel_db_id: int, platform: str, item: dict
    ) -> dict:
        """解析 API 返回的视频项为数据库模型字段字典"""
        video_id = item["id"]
        snippet = item.get("snippet", {})
        content = item.get("contentDetails", {})
        stats = item.get("statistics", {})
        live = item.get("liveStreamingDetails") or {}

        duration_fmt, total_secs = self.parse_duration(content.get("duration"))
        status = self.determine_video_status(item, total_secs)

        return {
            "channel_id": channel_db_id,
            "platform": platform,
            "video_id": video_id,
            "title": snippet.get("title"),
            "thumbnail_url": self.extract_thumbnail(snippet),
            "duration": duration_fmt,
            "duration_secs": total_secs if total_secs > 0 else None,
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats["likeCount"]) if stats.get("likeCount") else None,
            "status": status,
            "published_at": self.parse_datetime(snippet.get("publishedAt")),
            "scheduled_at": self.parse_datetime(live.get("scheduledStartTime")),
            "live_started_at": self.parse_datetime(live.get("actualStartTime")),
            "live_ended_at": self.parse_datetime(live.get("actualEndTime")),
            "live_chat_id": live.get("activeLiveChatId"),
        }

    def parse_channel_api_response(self, item: dict, channel_id: str) -> dict:
        """解析 API 返回的频道信息"""
        snippet = item.get("snippet", {})
        branding = item.get("brandingSettings", {})
        thumbnails = snippet.get("thumbnails", {})
        channel_branding = branding.get("channel", {})
        image_branding = branding.get("image", {})

        avatar_url = thumbnails.get("medium", {}).get("url") or thumbnails.get(
            "default", {}
        ).get("url")
        banner_url = (
            image_branding.get("bannerTvMediumUrl")
            or image_branding.get("bannerTvUrl")
            or image_branding.get("bannerUrl")
        )
        description = channel_branding.get("description") or snippet.get("description")

        return {
            "platform": Platform.YOUTUBE,
            "channel_id": channel_id,
            "name": snippet.get("title", ""),
            "avatar_url": avatar_url,
            "banner_url": banner_url,
            "description": description,
            "youtube_url": f"https://www.youtube.com/channel/{channel_id}",
        }

    def parse_channel_html(self, html_text: str, channel_id: str) -> Optional[dict]:
        """从 YouTube 频道 HTML 页面中提取基本信息（Fallback 模式）"""
        title_match = re.search(r"<title>([^<]+)</title>", html_text)
        title = None
        if title_match:
            title = html.unescape(
                title_match.group(1).replace(" - YouTube", "").strip()
            )

        avatar_match = re.search(
            r'"avatar":{"thumbnails":\[{"url":"([^"]+)"', html_text
        )
        avatar_url = None
        if avatar_match:
            avatar_url = self.clean_youtube_url(avatar_match.group(1))

        if title or avatar_url:
            return {
                "platform": Platform.YOUTUBE,
                "channel_id": channel_id,
                "name": title or "",
                "avatar_url": avatar_url,
            }
        return None