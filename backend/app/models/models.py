from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    BigInteger,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Boolean,
    Text,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    channels = relationship("UserChannel", back_populates="user")


class UserChannel(Base):
    __tablename__ = "user_channels"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    status = Column(String(20), nullable=False)  # "liked" 或 "blocked"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="channels")
    channel = relationship("Channel", back_populates="user_channels")

    __table_args__ = (
        Index("ix_user_channel_user_status", "user_id", "status"),
        Index("ix_user_channel_unique", "user_id", "channel_id", "status", unique=True),
    )


class Platform(str, enum.Enum):
    YOUTUBE = "youtube"
    BILIBILI = "bilibili"


class StreamStatus(str, enum.Enum):
    LIVE = "live"
    UPCOMING = "upcoming"
    ARCHIVE = "archive"
    OFFLINE = "offline"


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    name_en = Column(String(100), nullable=True)
    logo_url = Column(String(500), nullable=True)
    logo_shape = Column(String(10), default="circle")
    website = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    channels = relationship("Channel", back_populates="organization")


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    platform = Column(SQLEnum(Platform), nullable=False)
    channel_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    name_en = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    avatar_shape = Column(String(10), default="circle")
    banner_url = Column(String(500), nullable=True)
    twitter_url = Column(String(200), nullable=True)
    youtube_url = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    videos_last_fetched = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc)
    )

    organization = relationship("Organization", back_populates="channels")
    streams = relationship("Stream", back_populates="channel")
    videos = relationship("Video", back_populates="channel")
    user_channels = relationship("UserChannel", back_populates="channel")

    __table_args__ = (Index("ix_channel_platform_active", "platform", "is_active"),)


class Stream(Base):
    """直播/录播条目 — 一次直播事件"""

    __tablename__ = "streams"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    platform = Column(SQLEnum(Platform), nullable=False)
    video_id = Column(String(100), nullable=True, index=True)
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    viewer_count = Column(Integer, default=0)
    peak_viewers = Column(Integer, default=0)
    status = Column(SQLEnum(StreamStatus), default=StreamStatus.OFFLINE, index=True)
    live_chat_id = Column(String(100), nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_secs = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=True)

    channel = relationship("Channel", back_populates="streams")

    __table_args__ = (
        Index("ix_stream_status_platform", "status", "platform"),
        Index("ix_stream_channel_status", "channel_id", "status"),
    )


class Video(Base):
    """频道视频存储表"""

    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    platform = Column(SQLEnum(Platform), nullable=False)
    video_id = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    duration = Column(String(20), nullable=True)
    view_count = Column(Integer, default=0)
    published_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="archive")
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    channel = relationship("Channel", back_populates="videos")

    __table_args__ = (
        Index("ix_video_channel_published", "channel_id", "published_at"),
        Index("ix_video_unique", "channel_id", "video_id", unique=True),
    )


class Danmaku(Base):
    """弹幕存储表"""

    __tablename__ = "danmakus"

    id = Column(Integer, primary_key=True, index=True)
    stream_id = Column(Integer, ForeignKey("streams.id"), nullable=False, index=True)
    video_id = Column(String(100), nullable=False)
    messages = Column(Text, nullable=False)
    source = Column(String(20), default="youtube")
    downloaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    stream = relationship("Stream", backref="danmakus")
