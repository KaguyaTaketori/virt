from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database import SessionLocal
from app.schemas.schemas import StreamResponse
from app.models.models import Stream, StreamStatus, Channel, Platform
from datetime import datetime

router = APIRouter(prefix="/api/streams", tags=["streams"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/live", response_model=List[StreamResponse])
def get_live_streams(db: Session = Depends(get_db)):
    """
    获取当前正在直播的列表
    """
    streams = (
        db.query(Stream)
        .join(Channel, Stream.channel_id == Channel.id)
        .filter(Stream.status == StreamStatus.LIVE)
        .all()
    )

    result = []
    for stream in streams:
        result.append(StreamResponse(
            id=stream.id,
            channel_id=stream.channel_id,
            platform=stream.platform,
            video_id=stream.video_id,
            title=stream.title,
            thumbnail_url=stream.thumbnail_url,
            viewer_count=stream.viewer_count,
            status=stream.status,
            started_at=stream.started_at,
            channel_name=stream.channel.name if stream.channel else None,
            channel_avatar=stream.channel.avatar_url if stream.channel else None
        ))
    return result


@router.get("", response_model=List[StreamResponse])
def get_all_streams(
    platform: str = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    """
    获取所有直播列表，可按平台和状态筛选
    """
    query = db.query(Stream).join(Channel, Stream.channel_id == Channel.id)
    
    if platform:
        query = query.filter(Stream.platform == platform)
    if status:
        query = query.filter(Stream.status == status)
    
    streams = query.all()
    
    result = []
    for stream in streams:
        result.append(StreamResponse(
            id=stream.id,
            channel_id=stream.channel_id,
            platform=stream.platform,
            video_id=stream.video_id,
            title=stream.title,
            thumbnail_url=stream.thumbnail_url,
            viewer_count=stream.viewer_count,
            status=stream.status,
            started_at=stream.started_at,
            channel_name=stream.channel.name if stream.channel else None,
            channel_avatar=stream.channel.avatar_url if stream.channel else None
        ))
    return result