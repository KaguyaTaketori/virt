/**
 * frontend/src/utils/presetLayouts.ts（GridStack 版本）
 *
 * 预设布局生成器，返回 GridItem[] 数组
 */
import { type GridItem, type LayoutChannel } from '@/types/multiview'

function generateId() {
  return Math.random().toString(36).substring(2, 9)
}

function createEmptyChannel(): LayoutChannel {
  return { platform: 'empty', id: `empty-${generateId()}` }
}

function L(channels: LayoutChannel[], i: number): LayoutChannel {
  return channels[i] ?? createEmptyChannel()
}

export type PresetId = '1-s' | '2-h' | '2-v' | '3-1+2' | '3-cols' | '4-grid' | '4-1+3'

function makeItem(x: number, y: number, w: number, h: number, channel: LayoutChannel): GridItem {
  return { id: generateId(), x, y, w, h, channel }
}

export const PRESET_GENERATORS: Record<PresetId, (channels: LayoutChannel[]) => GridItem[]> = {
  '1-s': (v) => [
    makeItem(0, 0, 12, 12, L(v, 0)),
  ],

  '2-h': (v) => [
    makeItem(0, 0, 6, 12, L(v, 0)),
    makeItem(6, 0, 6, 12, L(v, 1)),
  ],

  '2-v': (v) => [
    makeItem(0, 0, 12, 6, L(v, 0)),
    makeItem(0, 6, 12, 6, L(v, 1)),
  ],

  '3-1+2': (v) => [
    makeItem(0, 0, 8, 12, L(v, 0)),
    makeItem(8, 0, 4, 6, L(v, 1)),
    makeItem(8, 6, 4, 6, L(v, 2)),
  ],

  '3-cols': (v) => [
    makeItem(0, 0, 4, 12, L(v, 0)),
    makeItem(4, 0, 4, 12, L(v, 1)),
    makeItem(8, 0, 4, 12, L(v, 2)),
  ],

  '4-grid': (v) => [
    makeItem(0, 0, 6, 6, L(v, 0)),
    makeItem(6, 0, 6, 6, L(v, 1)),
    makeItem(0, 6, 6, 6, L(v, 2)),
    makeItem(6, 6, 6, 6, L(v, 3)),
  ],

  '4-1+3': (v) => [
    makeItem(0, 0, 9, 12, L(v, 0)),
    makeItem(9, 0, 3, 4, L(v, 1)),
    makeItem(9, 4, 3, 4, L(v, 2)),
    makeItem(9, 8, 3, 4, L(v, 3)),
  ],
}

export const PRESET_GROUPS = [
  { label: '1本视频', items: ['1-s'] as PresetId[] },
  { label: '2本视频', items: ['2-h', '2-v'] as PresetId[] },
  { label: '3本视频', items: ['3-1+2', '3-cols'] as PresetId[] },
  { label: '4本视频', items: ['4-grid', '4-1+3'] as PresetId[] },
]

export const PRESET_META: Record<PresetId, { label: string }> = {
  '1-s'  : { label: '单窗口模式' },
  '2-h'  : { label: '左右对半分割' },
  '2-v'  : { label: '上下对半分割' },
  '3-1+2': { label: '1大 + 2小' },
  '3-cols': { label: '三列并行' },
  '4-grid': { label: '2×2 田字格' },
  '4-1+3': { label: '1大 + 3小' },
}

export function getPresetMeta(id: string) {
  return PRESET_META[id as PresetId] || { label: id }
}