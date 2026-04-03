import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  type LayoutNode, type Channel,
  createEmptyLeaf, addChannelToTree,
  removeNodeAndMerge, getActiveChannels,
} from '@/utils/layoutEngine'

const STORAGE_KEY = 'multiview_tree'

export const useMultiviewStore = defineStore('multiview', () => {
  const tree = ref<LayoutNode>(createEmptyLeaf())

  function init() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) tree.value = JSON.parse(saved)
    } catch {}
  }

  function _persist() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tree.value))
  }

  const activeChannels = computed(() => getActiveChannels(tree.value))

  function addChannel(channel: Channel) {
    addChannelToTree(tree.value, channel)
    _persist()
  }

  function closeChannel(nodeId: string) {
    removeNodeAndMerge(tree.value, nodeId)
    _persist()
  }

  function clearChannel(nodeId: string) {
    function clear(node: LayoutNode) {
      if (node.id === nodeId && node.type === 'leaf')
        node.channel = { platform: 'empty', id: `empty-${Date.now()}` }
      else if (node.children) { clear(node.children[0]); clear(node.children[1]) }
    }
    clear(tree.value)
    _persist()
  }

  function replaceChannel(nodeId: string, channel: Channel) {
    function replace(node: LayoutNode) {
      if (node.id === nodeId) node.channel = channel
      else if (node.children) { replace(node.children[0]); replace(node.children[1]) }
    }
    replace(tree.value)
    _persist()
  }

  function loadFromShare(channels: Channel[]) {
    tree.value = createEmptyLeaf()
    channels.forEach(ch => addChannelToTree(tree.value, ch))
    _persist()
  }

  function saveTree() {
    _persist()
  }

  return { tree, activeChannels, init, addChannel, closeChannel, clearChannel, replaceChannel, loadFromShare, saveTree }
})