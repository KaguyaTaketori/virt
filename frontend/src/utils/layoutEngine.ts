// src/utils/layoutEngine.ts
export interface Channel {
  platform: 'youtube' | 'bilibili' | 'empty'
  id: string
  danmakuEnabled?: boolean
}

export interface LayoutNode {
  id: string
  type: 'split' | 'leaf'
  direction?: 'horizontal' | 'vertical' // split 节点专属
  ratio?: number // split 节点专属：0.1 ~ 0.9
  children?: [LayoutNode, LayoutNode] // split 节点必定有 2 个子节点
  channel?: Channel // leaf 节点专属
}

const PRESET_METADATA: Record<string, { label: string; icon?: string }> = {
  '1-s':     { label: '单窗口模式' },
  '2-h':     { label: '左右对半分割' },
  '2-v':     { label: '上下对半分割' },
  '3-1+2':   { label: '1大 🎞️ + 2小' },
  '3-cols':  { label: '三列纵向并行' },
  '4-grid':  { label: '2 × 2 田字格' },
  '4-1+3':   { label: '1大 🎞️ + 3小' },

};

export function getPresetMeta(id: string) {
  return PRESET_METADATA[id] || { label: id };
}

export function generateId() {
  return Math.random().toString(36).substring(2, 9)
}

export function createLeaf(channel: Channel): LayoutNode {
  return { id: generateId(), type: 'leaf', channel }
}

export function createEmptyLeaf(): LayoutNode {
  return createLeaf({ platform: 'empty', id: `empty-${generateId()}` })
}

// 获取树中所有的视频 (剔除 empty)
export function getActiveChannels(node: LayoutNode): Channel[] {
  if (node.type === 'leaf') {
    return node.channel?.platform !== 'empty' && node.channel ? [node.channel] : []
  }
  return [...getActiveChannels(node.children![0]), ...getActiveChannels(node.children![1])]
}

// 计算每个叶子节点的相对面积 (宽 x 高)，找出最大的节点
function findLargestLeaf(node: LayoutNode, w: number, h: number): { node: LayoutNode, area: number, w: number, h: number } {
  if (node.type === 'leaf') return { node, area: w * h, w, h }
  
  const ratio = node.ratio || 0.5
  let left, right
  if (node.direction === 'horizontal') {
    left = findLargestLeaf(node.children![0], w * ratio, h)
    right = findLargestLeaf(node.children![1], w * (1 - ratio), h)
  } else {
    left = findLargestLeaf(node.children![0], w, h * ratio)
    right = findLargestLeaf(node.children![1], w, h * (1 - ratio))
  }
  return left.area >= right.area ? left : right
}

// 寻找第一个 empty 节点
function findFirstEmpty(node: LayoutNode): LayoutNode | null {
  if (node.type === 'leaf') return node.channel?.platform === 'empty' ? node : null
  return findFirstEmpty(node.children![0]) || findFirstEmpty(node.children![1])
}

// 添加视频：优先填补空位，否则切分最大面积的窗口
export function addChannelToTree(root: LayoutNode, channel: Channel) {
  const emptyNode = findFirstEmpty(root)
  if (emptyNode) {
    emptyNode.channel = channel
    return
  }

  // 没有空位，切分最大的
  const { node: target, w, h } = findLargestLeaf(root, 1, 1)
  const oldChannel = target.channel
  
  target.type = 'split'
  // 根据长宽比决定横切还是竖切
  target.direction = w > h ? 'horizontal' : 'vertical'
  target.ratio = 0.5
  delete target.channel
  
  target.children = [
    createLeaf(oldChannel!),
    createLeaf(channel)
  ]
}

// 查找目标节点的父节点以及它是左(0)还是右(1)孩子
function findParent(root: LayoutNode, targetId: string): { parent: LayoutNode, index: 0 | 1 } | null {
  if (root.type === 'leaf') return null
  if (root.children![0].id === targetId) return { parent: root, index: 0 }
  if (root.children![1].id === targetId) return { parent: root, index: 1 }
  
  return findParent(root.children![0], targetId) || findParent(root.children![1], targetId)
}

// 彻底关闭并吞并
export function removeNodeAndMerge(root: LayoutNode, targetId: string) {
  if (root.id === targetId) { // 如果是根节点
    Object.assign(root, createEmptyLeaf())
    return
  }
  
  const res = findParent(root, targetId)
  if (!res) return
  
  const { parent, index } = res
  const sibling = parent.children![index === 0 ? 1 : 0]
  
  // 兄弟节点直接取代父节点的位置（这就是“吞并”）
  parent.type = sibling.type
  parent.direction = sibling.direction
  parent.ratio = sibling.ratio
  parent.children = sibling.children
  parent.channel = sibling.channel
}

// 拖拽交换两个叶子节点的内容
export function swapNodes(root: LayoutNode, idA: string, idB: string) {
  let nodeA: LayoutNode | null = null
  let nodeB: LayoutNode | null = null
  
  function findNodes(node: LayoutNode) {
    if (node.id === idA) nodeA = node
    if (node.id === idB) nodeB = node
    if (node.type === 'split') {
      findNodes(node.children![0])
      findNodes(node.children![1])
    }
  }
  findNodes(root)
  
  if (nodeA && nodeB && (nodeA as LayoutNode).type === 'leaf' && (nodeB as LayoutNode).type === 'leaf') {
    const temp = (nodeA as LayoutNode).channel
    ;(nodeA as LayoutNode).channel = (nodeB as LayoutNode).channel
    ;(nodeB as LayoutNode).channel = temp
  }
}