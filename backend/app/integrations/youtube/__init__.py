from fastapi import Depends

from app.integrations.youtube.video_parser import VideoParser
from app.integrations.youtube.youtube_api_client import YouTubeApiClient
from app.integrations.youtube.youtube_sync_service import YouTubeSyncService


def get_yt_api_client() -> YouTubeApiClient:
    return YouTubeApiClient()

def get_yt_parser() -> VideoParser:
    return VideoParser()

def get_youtube_sync_service() -> YouTubeSyncService:
    return YouTubeSyncService(YouTubeApiClient(), VideoParser())