<script setup lang="ts">
import { ref, provide, computed } from 'vue'
import { LayoutNode, swapNodes } from '@/utils/layoutEngine'
import SplitPaneNode from './SplitPaneNode.vue'
import { LayoutGrid } from 'lucide-vue-next'
import { useEventListener } from '@vueuse/core';

const props = defineProps<{
  layoutTree: LayoutNode
  showDanmaku: boolean
  danmakuSettings: any
}>()

const emit = defineEmits<{ 
  (e: 'requestAdd'): void
  (e: 'requestReplace', nodeId: string): void
  (e: 'clearChannel', nodeId: string): void
  (e: 'closeChannel', nodeId: string): void
  (e: 'toggleDanmaku', channelId: string, enabled: boolean): void
}>()

// --- 全局拖拽防吞噬机制 ---
const isDragging = ref(false)
const draggedNodeId = ref<string | null>(null)

function onDragStart(event: DragEvent, id: string) {
  isDragging.value = true
  draggedNodeId.value = id
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', id)
  }
}

function onDrop(targetId: string) {
  isDragging.value = false
  if (draggedNodeId.value && draggedNodeId.value !== targetId) {
    swapNodes(props.layoutTree, draggedNodeId.value, targetId)
  }
  draggedNodeId.value = null
}

// 监听拖拽结束（以防拖到窗口外部松手）
useEventListener(window, 'dragend', () => { isDragging.value = false })

// 将核心状态 Provider 给所有嵌套的节点
provide('isDragging', isDragging)
provide('showDanmaku', computed(() => props.showDanmaku))
provide('danmakuSettings', props.danmakuSettings)
provide('onDragStart', onDragStart)
provide('onDrop', onDrop)
provide('toggleDanmaku', (id: string, enabled: boolean) => emit('toggleDanmaku', id, enabled))
</script>

<template>
  <div class="flex-1 min-h-0 w-full relative bg-zinc-950">
    <!-- 全局透明遮罩层：只要在拖拽中，就盖住所有的 Iframe，防止事件被吞！ -->
    <div v-if="isDragging" class="absolute inset-0 z-50 bg-white/5 cursor-grabbing" @dragover.prevent @drop="isDragging = false"></div>

    <template v-if="layoutTree">
      <SplitPaneNode 
        :node="layoutTree"
        @clear="emit('clearChannel', $event)"
        @close="emit('closeChannel', $event)"
        @requestReplace="emit('requestReplace', $event)"
      />
    </template>

    <div v-else class="w-full h-full flex flex-col items-center justify-center gap-3 text-zinc-700">
      <LayoutGrid class="w-12 h-12 opacity-20" />
      <p class="text-sm">点击头部「添加」开始多窗观看</p>
    </div>
  </div>
</template>