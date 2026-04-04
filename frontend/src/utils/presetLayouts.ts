import { type Channel, type LayoutNode, createLeaf, generateId } from '@/utils/layoutEngine'

function split(
  direction: 'horizontal' | 'vertical',
  ratio: number,
  a: LayoutNode,
  b: LayoutNode,
): LayoutNode {
  return { id: generateId(), type: 'split', direction, ratio, children: [a, b] }
}

function L(channels: Channel[], i: number): LayoutNode {
  return createLeaf(channels[i] ?? { platform: 'empty', id: `empty-${generateId()}` })
}

export type PresetId = '1-s' | '2-h' | '2-v' | '3-1+2' | '3-cols' | '4-grid' | '4-1+3'

export const PRESET_GENERATORS: Record<PresetId, (channels: Channel[]) => LayoutNode> = {
  '1-s'  : (v) => L(v, 0),

  '2-h'  : (v) => split('horizontal', 0.5, L(v, 0), L(v, 1)),

  '2-v'  : (v) => split('vertical',   0.5, L(v, 0), L(v, 1)),

  '3-1+2': (v) => split('horizontal', 0.65,
    L(v, 0),
    split('vertical', 0.5, L(v, 1), L(v, 2)),
  ),

  '3-cols': (v) => split('horizontal', 0.33,
    L(v, 0),
    split('horizontal', 0.5, L(v, 1), L(v, 2)),
  ),

  '4-grid': (v) => split('horizontal', 0.5,
    split('vertical', 0.5, L(v, 0), L(v, 2)),
    split('vertical', 0.5, L(v, 1), L(v, 3)),
  ),

  '4-1+3': (v) => split('horizontal', 0.75,
    L(v, 0),
    split('vertical', 0.33,
      L(v, 1),
      split('vertical', 0.5, L(v, 2), L(v, 3)),
    ),
  ),
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