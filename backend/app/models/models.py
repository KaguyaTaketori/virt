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


class Platform(str, enum.Enum):
    YOUTUBE = "youtube"
    BILIBILI = "bilibili"


class StreamStatus(str, enum.Enum):
    LIVE = "live"
    UPCOMING = "upcoming"
    ARCHIVE = "archive"  # 录播
    OFFLINE = "offline"  # 频道无直播，不显示


class Organization(Base):
    """机构/事务所，如 Hololive、Nijisanji、VSPO 等"""

    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # "Hololive"
    name_en = Column(String(100), nullable=True)  # 英文别名
    logo_url = Column(String(500), nullable=True)
    website = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    channels = relationship("Channel", back_populates="organization")


class Channel(Base):
    """主播频道 — 一个主播在一个平台上的身份"""

    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    platform = Column(SQLEnum(Platform), nullable=False)
    channel_id = Column(String(100), unique=True, nullable=False)  # UC... / 房间号
    name = Column(String(100), nullable=False)
    name_en = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)  # 软删除/暂停追踪
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc)
    )

    organization = relationship("Organization", back_populates="channels")
    streams = relationship("Stream", back_populates="channel")

    __table_args__ = (Index("ix_channel_platform_active", "platform", "is_active"),)


class Stream(Base):
    """直播/录播条目 — 一次直播事件"""

    __tablename__ = "streams"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    platform = Column(SQLEnum(Platform), nullable=False)
    video_id = Column(
        String(100), nullable=True, index=True
    )  # YouTube videoId / B站 bvid
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    viewer_count = Column(Integer, default=0)
    peak_viewers = Column(Integer, default=0)
    status = Column(SQLEnum(StreamStatus), default=StreamStatus.OFFLINE, index=True)
    live_chat_id = Column(String(100), nullable=True)  # YouTube live chat ID
    scheduled_at = Column(DateTime, nullable=True)  # Upcoming 预定时间
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_secs = Column(Integer, nullable=True)  # 录播时长（秒）
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=True)

    channel = relationship("Channel", back_populates="streams")

    __table_args__ = (
        # 最常用的查询：当前直播列表、按平台筛选
        Index("ix_stream_status_platform", "status", "platform"),
        # 轮询更新时按 channel 查最新
        Index("ix_stream_channel_status", "channel_id", "status"),
    )


class Danmaku(Base):
    """弹幕存储表"""

    __tablename__ = "danmakus"

    id = Column(Integer, primary_key=True, index=True)
    stream_id = Column(Integer, ForeignKey("streams.id"), nullable=False, index=True)
    video_id = Column(String(100), nullable=False)
    messages = Column(Text, nullable=False)  # JSON字符串
    source = Column(String(20), default="youtube")  # youtube/bilibili
    downloaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    stream = relationship("Stream", backref="danmakus")
