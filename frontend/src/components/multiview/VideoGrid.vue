<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { GridStack, type GridItemHTMLElement } from 'gridstack'
import 'gridstack/dist/gridstack.min.css'
import { useMultiviewStore } from '@/stores/multiview'
import VideoCell from './VideoCell.vue'

defineProps<{
  showDanmaku: boolean
}>()

const store = useMultiviewStore()
const gridContainerRef = ref<HTMLElement | null>(null)
let grid: GridStack | null = null

let isInternalUpdate = false 

function initGrid() {
  if (!gridContainerRef.value) return

  const containerHeight = gridContainerRef.value.offsetHeight
  const rowHeight = containerHeight / 12

  grid = GridStack.init({
    column: 12,
    row: 12,
    cellHeight: rowHeight,
    margin: 4,
    float: true,
    animate: true,
    draggable: { handle: '.drag-handle' },
    resizable: { handles: 'se' }
  }, gridContainerRef.value)

  grid.on('change', (event, items) => {
    isInternalUpdate = true
    items?.forEach(item => {
      if (item.id) {
        store.updateItemPosition(
          item.id as string, 
          item.x || 0, 
          item.y || 0, 
          item.w || 4, 
          item.h || 4
        )
      }
    })
    setTimeout(() => { isInternalUpdate = false }, 100)
  })
}

async function syncLayout() {
  if (!grid || isInternalUpdate) return
  
  await nextTick()
  await nextTick()

  const els = Array.from(gridContainerRef.value?.querySelectorAll('.grid-stack-item') || []) as GridItemHTMLElement[]
  
  grid.batchUpdate()

  els.forEach(el => {
    if (!el.gridstackNode) {
      const id = el.getAttribute('gs-id')
      const item = store.items.find(i => i.id === id)
      grid!.makeWidget(el, {
        x: item?.x,
        y: item?.y,
        w: item?.w,
        h: item?.h,
        autoPosition: false
      })
    }
  })

  store.items.forEach(item => {
    const el = els.find(e => e.getAttribute('gs-id') === item.id)
    if (el) {
      grid!.update(el, { 
        x: item.x, 
        y: item.y, 
        w: item.w, 
        h: item.h,
        autoPosition: false 
      })
    }
  })

  const storeIds = new Set(store.items.map(i => i.id))
  const currentWidgets = grid.getGridItems()
  currentWidgets.forEach(w => {
    const id = w.getAttribute('gs-id')
    if (!id || !storeIds.has(id)) {
      grid!.removeWidget(w, false) 
    }
  })

  grid.batchUpdate(false)
}

watch(() => store.items, () => syncLayout(), { deep: true })

const handleResize = () => {
  if (grid && gridContainerRef.value) {
    grid.cellHeight(gridContainerRef.value.offsetHeight / 12)
  }
}

onMounted(() => {
  initGrid()
  syncLayout()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  grid?.destroy(false)
})

const emit = defineEmits<{ (e: 'requestReplace', nodeId: string): void }>()
</script>

<template>
  <div class="flex-1 min-h-0 w-full relative bg-zinc-950 p-1 overflow-hidden">
    <div ref="gridContainerRef" class="grid-stack">
      <!-- 关键修复：添加 gs-x, gs-y, gs-w, gs-h 属性绑定 -->
      <div
        v-for="item in store.items"
        :key="item.id"
        class="grid-stack-item"
        :gs-id="item.id"
        :gs-x="item.x"
        :gs-y="item.y"
        :gs-w="item.w"
        :gs-h="item.h"
      >
        <div class="grid-stack-item-content">
          <VideoCell 
            :item="item"
            :show-danmaku="showDanmaku"
            :danmaku-settings="store.danmakuSettings"
            @clear="store.clearChannel"
            @close="store.closeChannel"
            @request-replace="emit('requestReplace', $event)"
            @toggle-danmaku="store.toggleDanmaku"
          />
        </div>
      </div>
    </div>

    <div v-if="store.items.length === 0" class="absolute inset-0 flex flex-col items-center justify-center gap-3 text-zinc-700 pointer-events-none">
      <p class="text-sm font-medium">点击头部“添加”按钮或选择一个分组开始</p>
    </div>
  </div>
</template>

<style scoped>
.grid-stack { min-height: 100%; height: 100%; }
.grid-stack-item-content { overflow: hidden !important; background: #000; border-radius: 4px; }
:deep(.grid-stack-placeholder > .placeholder-content) {
  background: rgba(244, 63, 94, 0.1) !important;
  border: 2px dashed #f43f5e !important;
  border-radius: 4px;
}
</style>