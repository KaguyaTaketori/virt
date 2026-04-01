from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.deps import get_db
from app.schemas.schemas import StreamResponse
from app.models.models import Stream, StreamStatus, Channel

router = APIRouter(prefix="/api/streams", tags=["streams"])


@router.get("/live", response_model=List[StreamResponse])
def get_live_streams(db: Session = Depends(get_db)):
    """获取当前正在直播的列表。"""
    streams = (
        db.query(Stream)
        .join(Channel, Stream.channel_id == Channel.id)
        .filter(Stream.status == StreamStatus.LIVE)
        .all()
    )
    return [_to_response(s) for s in streams]


@router.get("", response_model=List[StreamResponse])
def get_all_streams(
    platform: str = None,
    status: str = None,
    db: Session = Depends(get_db),
):
    """获取所有直播列表，可按平台和状态筛选。"""
    query = db.query(Stream).join(Channel, Stream.channel_id == Channel.id)

    if platform:
        query = query.filter(Stream.platform == platform)
    if status:
        query = query.filter(Stream.status == status)

    return [_to_response(s) for s in query.all()]


def _to_response(stream: Stream) -> StreamResponse:
    """将 Stream ORM 对象转为 StreamResponse，集中处理关联字段。"""
    ch = stream.channel
    return StreamResponse(
        id=stream.id,
        channel_id=stream.channel_id,
        platform=stream.platform,
        video_id=stream.video_id,
        title=stream.title,
        thumbnail_url=stream.thumbnail_url,
        viewer_count=stream.viewer_count,
        status=stream.status,
        started_at=stream.started_at,
        scheduled_at=stream.scheduled_at,
        channel_name=ch.name if ch else None,
        channel_avatar=ch.avatar_url if ch else None,
        channel_avatar_shape=ch.avatar_shape if ch else None,
        org_id=ch.org_id if ch else None,
    )