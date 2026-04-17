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