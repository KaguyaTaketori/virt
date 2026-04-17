import { type GridItem, type LayoutChannel, type PresetId } from '@/types/multiview'

export type { LayoutChannel }

const generateId = () => Math.random().toString(36).substring(2, 9)

/**
 * 辅助函数：创建布局项目
 * 这里的 h 参数确保了在 12 行网格系统中的高度
 */
function makeItem(x: number, y: number, w: number, h: number, channel?: LayoutChannel): GridItem {
  return { 
    id: generateId(), 
    x, y, w, h, 
    channel: channel || { platform: 'empty', id: `empty-${generateId()}` }
  };
}

// 快捷获取通道
const L = (v: LayoutChannel[], i: number) => v[i];

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
    makeItem(0, 0, 8, 12, L(v, 0)), // 左侧大屏
    makeItem(8, 0, 4, 6,  L(v, 1)), // 右上小屏
    makeItem(8, 6, 4, 6,  L(v, 2)), // 右下小屏
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
    makeItem(0, 0, 9, 12, L(v, 0)), // 左侧主屏
    makeItem(9, 0, 3, 4,  L(v, 1)), // 右侧小屏1
    makeItem(9, 4, 3, 4,  L(v, 2)), // 右侧小屏2
    makeItem(9, 8, 3, 4,  L(v, 3)), // 右侧小屏3
  ],
}

export const PRESET_META: Record<PresetId, { label: string }> = {
  '1-s'  : { label: '单窗口模式' },
  '2-h'  : { label: '左右平分' },
  '2-v'  : { label: '上下平分' },
  '3-1+2': { label: '1主 + 2侧' },
  '3-cols': { label: '三列并行' },
  '4-grid': { label: '2x2 田字格' },
  '4-1+3': { label: '1主 + 3侧' },
}

export const PRESET_GROUPS = [
  { label: '1本视频', items: ['1-s'] as PresetId[] },
  { label: '2本视频', items: ['2-h', '2-v'] as PresetId[] },
  { label: '3本视频', items: ['3-1+2', '3-cols'] as PresetId[] },
  { label: '4本视频', items: ['4-grid', '4-1+3'] as PresetId[] },
]