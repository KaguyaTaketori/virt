<script setup lang="ts">
import { ref, watch, toRef, onUnmounted } from 'vue'
import { useElementSize, useEventListener } from '@vueuse/core'
import { DEFAULT_DANMAKU_SETTINGS, type DanmakuSettings } from '@/types/danmaku'
import { useDanmakuEngine } from '@/composables/danmaku/useDanmakuEngine'

interface Props {
  videoId: string
  platform: 'youtube' | 'bilibili'
  enabled: boolean
  settings?: DanmakuSettings
}

const props = defineProps<Props>()

const containerRef = ref<HTMLDivElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const hitLayerRef = ref<HTMLDivElement | null>(null)
const { width, height } = useElementSize(containerRef)

const settings = ref<DanmakuSettings>({ ...DEFAULT_DANMAKU_SETTINGS })
watch(() => props.settings, (s) => { 
  if (s) { 
    Object.assign(settings.value, s)
    engine.applyCanvasFont()
  } 
}, { deep: true })

const engine = useDanmakuEngine({
  videoId: toRef(props, 'videoId'),
  platform: toRef(props, 'platform'),
  enabled: toRef(props, 'enabled'),
  settings,
  width,
  height,
  hitLayerRef,
  canvasRef
})

const { hoveredDanmaku } = engine

useEventListener(hitLayerRef, 'mouseover', (e) => {
  const target = e.target as HTMLElement
  if (target.classList.contains('danmaku-ghost')) {
    const msgId = target.dataset.messageId
    if (hoveredDanmaku.value.messageId !== msgId) {
      engine.stopHideTimer()
      engine.startForceResumeTimer()
      
      const danmaku = engine.activeDanmaku.value.find(item => item.msg.messageId === msgId)
      if (danmaku) {
        const rect = target.getBoundingClientRect()
        hoveredDanmaku.value = {
          show: true,
          x: rect.left,
          y: rect.bottom + 5,
          userId: target.dataset.userId || '',
          displayName: target.dataset.displayName || '',
          messageId: msgId!
        }
      }
    }
  }
})

useEventListener(hitLayerRef, 'mouseout', (e) => {
  if ((e.target as HTMLElement).classList.contains('danmaku-ghost')) {
    engine.startHideTimer()
  }
})

function handleMenuEnter() {
  engine.stopHideTimer()
}

watch(() => props.enabled, (val) => {
  if (val) engine.resume()
  else { engine.pause(); engine.clearAll() }
}, { immediate: true })

watch(() => props.videoId, () => engine.clearAll())

onUnmounted(() => {
  engine.disconnect()
  engine.clearAll()
})
</script>

<template>
  <div v-if="enabled" ref="containerRef" class="absolute inset-0 overflow-hidden pointer-events-none z-20">
    <canvas ref="canvasRef" class="absolute inset-0 w-full h-full pointer-events-none" />
    <div ref="hitLayerRef" class="absolute inset-0 pointer-events-none" />
    
    <!-- 操作菜单 -->
    <div
      v-if="hoveredDanmaku.show"
      class="fixed bg-zinc-800/95 rounded-lg shadow-xl z-50 py-2 min-w-[140px] pointer-events-auto border border-zinc-700"
      :style="{ left: hoveredDanmaku.x + 'px', top: hoveredDanmaku.y + 'px' }"
      @mouseenter="handleMenuEnter"
      @mouseleave="engine.startHideTimer"
    >
      <div class="px-3 py-1 text-xs text-zinc-400 border-b border-zinc-700 mb-1 truncate max-w-[140px]">
        {{ hoveredDanmaku.displayName || hoveredDanmaku.userId }}
      </div>
      <button 
        class="w-full px-4 py-1.5 text-left text-sm hover:bg-zinc-700 transition-colors text-white" 
        @click="engine.handleHighlightUser"
      >
        高亮此人
      </button>
      <button 
        class="w-full px-4 py-1.5 text-left text-sm hover:bg-zinc-700 transition-colors text-rose-400" 
        @click="engine.handleBlockUser"
      >
        屏蔽用户
      </button>
    </div>
  </div>
</template>