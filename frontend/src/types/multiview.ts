export type GroupSelection =
  | { kind: 'favorites' }
  | { kind: 'org'; orgId: number }
  | null

export interface LayoutChannel {
  platform: 'youtube' | 'bilibili' | 'empty'
  id: string
  danmakuEnabled?: boolean
}

export interface GridItem {
  id: string
  x: number
  y: number
  w: number
  h: number
  channel: LayoutChannel
}

export type PresetId = '1-s' | '2-h' | '2-v' | '3-1+2' | '3-cols' | '4-grid' | '4-1+3'