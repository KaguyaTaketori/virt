export interface DanmakuSettings {
  enabled: boolean
  fontSize: number        // 12 ~ 48
  speed: number           // 0.5 ~ 6
  opacity: number         // 0.3 ~ 1
  color: string           // CSS color string
  strokeEnabled: boolean
  strokeColor: string
  strokeWidth: number     // 0 ~ 4
}

export const DEFAULT_DANMAKU_SETTINGS: Readonly<DanmakuSettings> = {
  enabled: false,
  fontSize: 24,
  speed: 2,
  opacity: 1,
  color: '#ffffff',
  strokeEnabled: true,
  strokeColor: '#000000',
  strokeWidth: 2,
}

export interface DanmakuMessage {
  messageId: string
  message_id?: string
  userId?: string
  user_id?: string
  user_display_name?: string
  comment: string
  message?: string
  message_type?: string
  sticker_url?: string
}

export interface ActiveDanmaku {
  msg: DanmakuMessage
  x: number
  y: number
  opacity: number
  textWidth: number
  isHovered: boolean 
}

// ── B 站用户信息（替换 ChannelDetail.vue 中的 bilibiliInfo: any）
export interface BilibiliUserInfo {
  mid: number | string
  name: string
  face: string
  sign: string | null
  fans: number | null
  attention: number | null
  archive_count: number | null
}

// ── B 站动态（替换 ChannelDetail.vue 中的隐式 any）
export interface BilibiliDynamic {
  dynamic_id: string
  type: number
  timestamp: number
  content: string
  images: string[]
  repost_content: string | null
}

// ── B 站视频
export interface BilibiliVideo {
  bvid: string
  title: string
  pic: string
  aid: number
  duration: number   // 原始秒数，由后端统一转换
  pubdate: number
  play: number
  like: number
  coin: number
  favorite: number
  share: number
  reply: number
}

// ── API 响应整体（与后端 channels/bilibili.py 对应）
export interface BilibiliChannelResponse {
  info: BilibiliUserInfo | null
  dynamics: BilibiliDynamic[]
  videos: BilibiliVideo[]
}