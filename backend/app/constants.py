from enum import StrEnum

# YouTube 视频时长分类阈值（秒）
YT_SHORT_MAX_SECS     = 61       # ≤ 61s 判定为 Shorts
YT_PREMIERE_SHORT     = 300      # < 5min 强烈倾向 Premiere
YT_PREMIERE_MEDIUM    = 600      # < 10min 中等倾向 Premiere
YT_PREMIERE_LONG      = 1800     # < 30min 弱倾向 Premiere
YT_LIVE_THRESHOLD     = 3600     # > 1h 倾向直播录播
YT_LIVE_STRONG        = 7200     # > 2h 强烈倾向直播录播

# Premiere 启发式评分阈值
PREMIERE_POSITIVE_THRESHOLD = 0  # score > 0 判定为 Premiere

# Bilibili 爬取限制
BILIBILI_MAX_VIDEO_PAGES   = 10
BILIBILI_DEFAULT_PAGE_SIZE = 30

# 弹幕
DANMAKU_MAX_ACTIVE       = 40    # canvas 上同时显示的最大弹幕数
DANMAKU_TRUNCATE_BATCH   = 50    # 单次推送截断阈值
DANMAKU_MAX_SEEN_IDS     = 10_000

# WebSocket
WS_HEARTBEAT_INTERVAL_SECS = 25


class UserRole(StrEnum):
    SUPERADMIN = "superadmin"
    ADMIN      = "admin"
    OPERATOR   = "operator"
    USER       = "user"

class ChannelStatus(StrEnum):
    ACTIVE    = "active"
    GRADUATED = "graduated"

class UserChannelStatus(StrEnum):
    LIKED   = "liked"
    BLOCKED = "blocked"

class Permission(StrEnum):
    BILIBILI_ACCESS = "bilibili.access"
    CHANNEL_MANAGE  = "channel.manage"
    SYSTEM_MANAGE   = "system.manage"

class PermissionResource(StrEnum):
    BILIBILI = "bilibili"
    CHANNEL  = "channel"
    SYSTEM   = "system"
    WEBSUB   = "websub"

class PermissionAction(StrEnum):
    ACCESS = "access"
    MANAGE = "manage"