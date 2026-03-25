from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class Platform(str, enum.Enum):
    YOUTUBE = "youtube"
    BILIBILI = "bilibili"


class StreamStatus(str, enum.Enum):
    LIVE = "live"
    UPCOMING = "upcoming"
    OFFLINE = "offline"


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(SQLEnum(Platform), nullable=False)
    channel_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    
    streams = relationship("Stream", back_populates="channel")


class Stream(Base):
    __tablename__ = "streams"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    platform = Column(SQLEnum(Platform), nullable=False)
    video_id = Column(String, nullable=True)
    title = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    viewer_count = Column(Integer, default=0)
    status = Column(SQLEnum(StreamStatus), default=StreamStatus.OFFLINE)
    started_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    channel = relationship("Channel", back_populates="streams")