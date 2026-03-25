from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database import SessionLocal
from app.schemas.schemas import ChannelCreate, ChannelResponse
from app.models.models import Channel

router = APIRouter(prefix="/api/channels", tags=["channels"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=List[ChannelResponse])
def get_channels(platform: str = None, db: Session = Depends(get_db)):
    query = db.query(Channel)
    if platform:
        query = query.filter(Channel.platform == platform)
    return query.all()


@router.post("", response_model=ChannelResponse)
def create_channel(channel: ChannelCreate, db: Session = Depends(get_db)):
    db_channel = Channel(**channel.model_dump())
    db.add(db_channel)
    db.commit()
    db.refresh(db_channel)
    return db_channel