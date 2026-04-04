/**
 * frontend/src/types/danmaku.ts
 *
 * 问题 14 修复：为弹幕设置、频道详情等提供具体类型，替换散落的 any。
 */

// ── 弹幕设置（替换 VideoGrid.vue 和 MultiView.vue 中的 danmakuSettings: any）
export interface DanmakuSettings {
  fontSize: number        // 12 ~ 48
  speed: number           // 0.5 ~ 6
  opacity: number         // 0.3 ~ 1
  color: string           // CSS color string
  strokeEnabled: boolean
  strokeColor: string
  strokeWidth: number     // 0 ~ 4
}

export const DEFAULT_DANMAKU_SETTINGS: Readonly<DanmakuSettings> = {
  fontSize: 24,
  speed: 2,
  opacity: 1,
  color: '#ffffff',
  strokeEnabled: true,
  strokeColor: '#000000',
  strokeWidth: 2,
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