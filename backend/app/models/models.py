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
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.database import Base
from app.utils.snowflake import generate_channel_id


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    bilibili_sessdata = Column(String(500), nullable=True)
    bilibili_bili_jct = Column(String(100), nullable=True)
    bilibili_buvid3 = Column(String(100), nullable=True)
    bilibili_dedeuserid = Column(String(100), nullable=True)

    channels = relationship("UserChannel", back_populates="user")
    user_roles = relationship("UserRole", back_populates="user")
    login_logs = relationship("UserLoginLog", back_populates="user")


class UserLoginLog(Base):
    """用户登录记录表"""

    __tablename__ = "user_login_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    ip_address = Column(String(45), nullable=True)  # 支持IPv6
    user_agent = Column(String(500), nullable=True)
    country = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    isp = Column(String(100), nullable=True)
    login_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    success = Column(Boolean, default=True)
    fail_reason = Column(String(200), nullable=True)

    user = relationship("User", back_populates="login_logs")

    __table_args__ = (Index("ix_user_login_log_user_login_at", "user_id", "login_at"),)


class UserChannel(Base):
    __tablename__ = "user_channels"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel_id = Column(BigInteger, ForeignKey("channels.id"), nullable=False)
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

    id = Column(
        BigInteger, primary_key=True, index=True, default=lambda: generate_channel_id()
    )
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
    twitch_url = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    group = Column(String(50), nullable=True)
    status = Column(String(20), default="active")
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

    bilibili_fans = Column(Integer, nullable=True)
    bilibili_sign = Column(Text, nullable=True)
    bilibili_archive_count = Column(Integer, nullable=True)
    bilibili_face = Column(String(500), nullable=True)
    bilibili_following = Column(Integer, nullable=True)

    __table_args__ = (Index("ix_channel_platform_active", "platform", "is_active"),)


class Stream(Base):
    """直播/录播条目 — 一次直播事件"""

    __tablename__ = "streams"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(BigInteger, ForeignKey("channels.id"), nullable=False)
    platform = Column(SQLEnum(Platform), nullable=False)
    video_id = Column(String(100), nullable=False, index=True)
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
        UniqueConstraint("channel_id", "video_id", name="uix_stream_channel_video"),
        Index("ix_stream_status_platform", "status", "platform"),
        Index("ix_stream_channel_status", "channel_id", "status"),
    )


class Video(Base):
    """频道视频存储表"""

    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(BigInteger, ForeignKey("channels.id"), nullable=False)
    platform = Column(SQLEnum(Platform), nullable=False)
    video_id = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    duration = Column(String(20), nullable=True)
    view_count = Column(Integer, default=0)
    published_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="archive")
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    duration_secs = Column(Integer, nullable=True)
    like_count = Column(BigInteger, nullable=True)
    live_chat_id = Column(String(100), nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    live_started_at = Column(DateTime, nullable=True)
    live_ended_at = Column(DateTime, nullable=True)

    channel = relationship("Channel", back_populates="videos")

    __table_args__ = (
        Index("ix_video_channel_published", "channel_id", "published_at"),
        Index("ix_video_unique", "channel_id", "video_id", unique=True),
    )


class BilibiliDynamic(Base):
    """B站动态存储表"""

    __tablename__ = "bilibili_dynamics"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(
        BigInteger, ForeignKey("channels.id"), nullable=False, index=True
    )
    dynamic_id = Column(String(50), unique=True, nullable=False)
    uid = Column(String(50))
    uname = Column(String(100))
    face = Column(String(500))
    type = Column(Integer)
    content_nodes = Column(Text)
    images = Column(Text)
    repost_content = Column(Text)
    timestamp = Column(Integer)
    published_at = Column(DateTime, nullable=True)
    url = Column(String(500))
    stat = Column(Text)
    topic = Column(String(200))
    is_top = Column(Boolean, default=False)
    raw_data = Column(Text)
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_bilibili_dynamic_channel_published", "channel_id", "published_at"),
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


# backend/app/models/models.py 末尾追加


class WebSubSubscription(Base):
    """记录每个 YouTube 频道的 WebSub/PubSubHubbub 订阅状态。"""

    __tablename__ = "websub_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(
        Integer,
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    topic_url = Column(String(300), nullable=False)
    hub_url = Column(String(300), nullable=False)
    secret = Column(String(100), nullable=True)
    verified = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=True)
    subscribed_at = Column(DateTime, nullable=True)
    last_push_at = Column(DateTime, nullable=True)
    push_count = Column(Integer, default=0)

    channel = relationship("Channel")


class Role(Base):
    """角色定义表"""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    users = relationship("UserRole", back_populates="role")
    permissions = relationship("RolePermission", back_populates="role")


class Permission(Base):
    """权限定义表"""

    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(200), nullable=True)
    resource = Column(String(50), nullable=False)  # channel, user, system, etc.
    action = Column(String(50), nullable=False)  # create, read, update, delete, manage
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    roles = relationship("RolePermission", back_populates="permission")


class UserRole(Base):
    """用户-角色关联表"""

    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id = Column(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="users")

    __table_args__ = (Index("ix_user_role_unique", "user_id", "role_id", unique=True),)


class RolePermission(Base):
    """角色-权限关联表"""

    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_id = Column(
        Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")

    __table_args__ = (
        Index("ix_role_permission_unique", "role_id", "permission_id", unique=True),
    )


class ResourceACL(Base):
    """用户-特定资源实例的ACL映射表（资源级权限）"""

    __tablename__ = "resource_acls"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    resource = Column(String(50), nullable=False)  # channel, organization, etc.
    resource_id = Column(Integer, nullable=False)  # 具体资源ID
    access = Column(String(20), nullable=False)  # owner, editor, viewer
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")

    __table_args__ = (
        Index(
            "ix_resource_acl_unique", "user_id", "resource", "resource_id", unique=True
        ),
        Index("ix_resource_acl_lookup", "resource", "resource_id"),
    )
