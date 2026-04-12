/**
 * frontend/src/stores/multiview.ts（增强版）
 *
 * 问题 13 修复：MultiView.vue 与此 store 存在逻辑重复。
 * 将 applyPreset、shareUrl、loadFromShareParam 等逻辑统一收归 store，
 * 视图层只负责 UI 事件转发，不再包含业务逻辑。
 */
import { defineStore } from 'pinia'
import { computed } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import {
  type LayoutNode,
  type LayoutChannel,
  createEmptyLeaf,
  addChannelToTree,
  removeNodeAndMerge,
  getActiveChannels,
} from '@/utils/layoutEngine'
import { PRESET_GENERATORS, type PresetId } from '@/utils/presetLayouts'

const STORAGE_KEY = 'multiview_tree'
const DANMAKU_SETTINGS_KEY = 'danmaku_settings'

export interface DanmakuSettings {
  enabled?: boolean
  fontSize: number
  speed: number
  opacity: number
  color: string
  strokeEnabled: boolean
  strokeColor: string
  strokeWidth: number
}

export const DEFAULT_DANMAKU_SETTINGS: DanmakuSettings = {
  enabled: false,
  fontSize: 24,
  speed: 2,
  opacity: 1,
  color: '#ffffff',
  strokeEnabled: true,
  strokeColor: '#000000',
  strokeWidth: 2,
}

export const useMultiviewStore = defineStore('multiview', () => {
  const tree = useLocalStorage<LayoutNode>(STORAGE_KEY, createEmptyLeaf())
  const activeChannels = computed(() => getActiveChannels(tree.value))

  const danmakuSettings = useLocalStorage<DanmakuSettings>(
    DANMAKU_SETTINGS_KEY,
    DEFAULT_DANMAKU_SETTINGS,
  )

  function updateDanmakuSettings(partial: Partial<DanmakuSettings>) {
    danmakuSettings.value = { ...danmakuSettings.value, ...partial }
  }

  function resetDanmakuSettings() {
    danmakuSettings.value = { ...DEFAULT_DANMAKU_SETTINGS }
  }

  // ── 频道操作 ───────────────────────────────────────────────────────────────
  function addChannel(channel: LayoutChannel) {
    addChannelToTree(tree.value, channel)
  }

  function closeChannel(nodeId: string) {
    removeNodeAndMerge(tree.value, nodeId)
  }

  function clearChannel(nodeId: string) {
    _traverseLeaf(tree.value, nodeId, (node) => {
      node.channel = { platform: 'empty', id: `empty-${Date.now()}` }
    })
  }

  function replaceChannel(nodeId: string, channel: LayoutChannel) {
    _traverseLeaf(tree.value, nodeId, (node) => { node.channel = channel })
  }

  function removeByPlatformId(platform: string, id: string) {
    function find(node: LayoutNode): boolean {
      if (node.type === 'leaf' && node.channel?.platform === platform && node.channel?.id === id) {
        closeChannel(node.id)
        return true
      }
      if (node.children) return find(node.children[0]) || find(node.children[1])
      return false
    }
    find(tree.value)
  }

  // ── 预设布局（问题 2 修复：使用 presetLayouts.ts，ID 唯一）───────────────
  function applyPreset(id: PresetId) {
    const generator = PRESET_GENERATORS[id]
    if (generator) {
      tree.value = generator(activeChannels.value)
    }
  }

  // ── 分享 ───────────────────────────────────────────────────────────────────
  function buildShareCode(): string {
    return btoa(activeChannels.value.map((c) => `${c.platform}_${c.id}`).join(','))
  }

  async function copyShareUrl(): Promise<void> {
    const code = buildShareCode()
    const url = `${window.location.origin}/multiview?c=${code}`
    await navigator.clipboard.writeText(url)
  }

  function loadFromShareParam(encoded: string): boolean {
    try {
      const list = atob(encoded)
        .split(',')
        .map((item) => {
          const [platform, id] = item.split('_')
          return { platform, id } as LayoutChannel
        })
        .filter((c) => c.platform && c.id)

      if (!list.length) return false

      tree.value = createEmptyLeaf()
      list.forEach((ch) => addChannelToTree(tree.value, ch))
      return true
    } catch {
      return false
    }
  }

  function addFromVideoId(platform: 'youtube' | 'bilibili', videoId: string) {
    if (!videoId) return
    const channel: LayoutChannel = { platform, id: videoId }
    const alreadyAdded = activeChannels.value.some(
      c => c.id === channel.id && c.platform === channel.platform
    )
    if (!alreadyAdded) {
      addChannelToTree(tree.value, channel)
    }
  }

  return {
    tree,
    activeChannels,
    danmakuSettings,
    updateDanmakuSettings,
    resetDanmakuSettings,
    addChannel,
    closeChannel,
    clearChannel,
    replaceChannel,
    removeByPlatformId,
    applyPreset,
    copyShareUrl,
    loadFromShareParam,
    addFromVideoId,
  }
})

// ── 内部工具 ──────────────────────────────────────────────────────────────────
function _traverseLeaf(
  node: LayoutNode,
  targetId: string,
  fn: (node: LayoutNode) => void,
) {
  if (node.id === targetId && node.type === 'leaf') {
    fn(node)
    return
  }
  if (node.children) {
    _traverseLeaf(node.children[0], targetId, fn)
    _traverseLeaf(node.children[1], targetId, fn)
  }
}