from app.integrations.youtube.video_parser import VideoParser
from app.integrations.youtube.youtube_api_client import YouTubeApiClient
from app.integrations.youtube.youtube_sync_service import YouTubeSyncService


def get_yt_api_client() -> YouTubeApiClient:
    return YouTubeApiClient()


def get_yt_parser() -> VideoParser:
    return VideoParser()


def get_youtube_sync_service() -> YouTubeSyncService:
    return YouTubeSyncService(api_client=get_yt_api_client(), parser=get_yt_parser())


def get_youtube_client():
    """兼容旧接口，返回 YouTubeSyncService 实例"""
    return get_youtube_sync_service()
