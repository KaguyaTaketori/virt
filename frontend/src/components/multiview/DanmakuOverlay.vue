<script setup lang="ts">
import { ref, watch, toRef, onUnmounted } from 'vue'
import { 
  useElementSize, 
  useRafFn, 
  useEventListener, 
  useTimeoutFn, 
  onClickOutside 
} from '@vueuse/core'
import { DEFAULT_DANMAKU_SETTINGS, type DanmakuSettings, type ActiveDanmaku } from '@/types/danmaku'
import { useDanmakuUsers } from '@/composables/useDanmakuUsers'
import { useDanmakuWS, useDanmakuHitLayer } from '@/composables/useDanmakuWS'

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
const menuRef = ref<HTMLDivElement | null>(null)
const ctx = ref<CanvasRenderingContext2D | null>(null)

const { blockUser, highlightUser, isBlocked } = useDanmakuUsers()
const { drainQueue, disconnect } = useDanmakuWS(
  toRef(props, 'videoId'),
  toRef(props, 'platform'),
  toRef(props, 'enabled')
)

const { 
  addGhostDiv, 
  removeGhostDiv, 
  clearAll: clearHitLayer, 
  updatePosition 
} = useDanmakuHitLayer(hitLayerRef)

const settings = ref<DanmakuSettings>({ ...DEFAULT_DANMAKU_SETTINGS })
const activeDanmaku = ref<ActiveDanmaku[]>([])
const hoveredDanmaku = ref({
  show: false, x: 0, y: 0, userId: '', displayName: '', messageId: ''
})

const { width: containerWidth, height: containerHeight } = useElementSize(containerRef)

function applyCanvasFont() {
  if (!ctx.value) return
  ctx.value.font = `bold ${settings.value.fontSize}px system-ui, sans-serif`
  ctx.value.textBaseline = 'top'
}

watch([containerWidth, containerHeight], ([w, h]) => {
  if (canvasRef.value && w > 0 && h > 0) {
    canvasRef.value.width = w
    canvasRef.value.height = h
    applyCanvasFont()
  }
})

const { start: startHideTimer, stop: stopHideTimer } = useTimeoutFn(() => {
  hoveredDanmaku.value.show = false
  const d = activeDanmaku.value.find(item => item.msg.messageId === hoveredDanmaku.value.messageId)
  if (d) d.isHovered = false
}, 250, { immediate: false })

function handleMenuEnter() {
  stopHideTimer()
  const d = activeDanmaku.value.find(item => item.msg.messageId === hoveredDanmaku.value.messageId)
  if (d) d.isHovered = true
}

onClickOutside(menuRef, () => {
  hoveredDanmaku.value.show = false
})

let lastTime = 0

const { pause, resume } = useRafFn(({ timestamp }) => {
  if (!ctx.value || !canvasRef.value || !props.enabled) return

  const deltaTime = lastTime ? (timestamp - lastTime) / 16.67 : 1
  lastTime = timestamp

  const { width, height } = canvasRef.value
  const context = ctx.value

  context.clearRect(0, 0, width, height)

  const { speed, opacity, color, strokeEnabled, strokeColor, strokeWidth, fontSize } = settings.value

  for (let i = activeDanmaku.value.length - 1; i >= 0; i--) {
    const danmaku = activeDanmaku.value[i]
    
    if (!danmaku.isHovered) {
      danmaku.x -= speed * deltaTime
    }

    if (danmaku.x + danmaku.textWidth < 0) {
      removeGhostDiv(danmaku.msg.messageId)
      activeDanmaku.value.splice(i, 1)
      continue
    }
    updatePosition(danmaku.msg.messageId, danmaku.x, danmaku.y)
  }

  const newMsgs = drainQueue()
  for (const msg of newMsgs) {
    if (msg.userId && isBlocked(msg.userId)) continue
    if (activeDanmaku.value.length > 40) break

    const mId = msg.messageId || `local_${Math.random().toString(36).slice(2)}`
    const textWidth = context.measureText(msg.comment).width
    const y = Math.random() * (height - fontSize - 20) + 10

    activeDanmaku.value.push({
      msg, x: width, y, opacity: 1, textWidth, isHovered: false
    })
    addGhostDiv(mId, msg.comment, width, y, textWidth, fontSize, msg.userId, msg.user_display_name)
  }

  context.globalAlpha = opacity
  for (const danmaku of activeDanmaku.value) {
    if (strokeEnabled) {
      context.strokeStyle = strokeColor
      context.lineWidth = strokeWidth
      context.strokeText(danmaku.msg.comment, danmaku.x, danmaku.y)
    }
    context.fillStyle = color
    context.fillText(danmaku.msg.comment, danmaku.x, danmaku.y)
  }
  context.globalAlpha = 1
}, { immediate: props.enabled })

useEventListener(hitLayerRef, 'mouseover', (e) => {
  const target = e.target as HTMLElement
  if (target.classList.contains('danmaku-ghost')) {
    const msgId = target.dataset.messageId
    if (!msgId) return

    stopHideTimer()
    const danmaku = activeDanmaku.value.find(item => item.msg.messageId === msgId)
    if (danmaku) {
      danmaku.isHovered = true
      const rect = target.getBoundingClientRect()
      hoveredDanmaku.value = {
        show: true,
        x: rect.left,
        y: rect.bottom + 5,
        userId: target.dataset.userId || '',
        displayName: target.dataset.displayName || '',
        messageId: msgId
      }
    }
  }
})

useEventListener(hitLayerRef, 'mouseout', (e) => {
  if ((e.target as HTMLElement).classList.contains('danmaku-ghost')) {
    startHideTimer()
  }
})

function handleBlockUser() {
  const { userId } = hoveredDanmaku.value
  if (!userId) return
  blockUser(userId)
  activeDanmaku.value = activeDanmaku.value.filter(d => {
    if (d.msg.userId === userId) {
      removeGhostDiv(d.msg.messageId)
      return false
    }
    return true
  })
  hoveredDanmaku.value.show = false
}

function handleHighlightUser() {
  if (hoveredDanmaku.value.userId) {
    highlightUser(hoveredDanmaku.value.userId)
  }
  hoveredDanmaku.value.show = false
}

function clearAll() {
  activeDanmaku.value = []
  clearHitLayer()
}

watch(() => canvasRef.value, (el) => {
  if (el) ctx.value = el.getContext('2d')
})

watch(() => props.settings, (s) => {
  if (s) {
    Object.assign(settings.value, s)
    applyCanvasFont()
  }
}, { deep: true })

watch(() => props.videoId, () => clearAll())

watch(() => props.enabled, (val) => {
  if (val) resume()
  else {
    pause()
    clearAll()
  }
}, { immediate: true })

onUnmounted(() => {
  disconnect()
  clearAll()
})
</script>

<template>
  <div 
    ref="containerRef"
    v-if="enabled" 
    class="absolute inset-0 overflow-hidden pointer-events-none z-20"
  >
    <canvas
      ref="canvasRef"
      class="absolute inset-0 w-full h-full pointer-events-none"
    />
    
    <div ref="hitLayerRef" class="absolute inset-0 pointer-events-none" />
    
    <div
      v-if="hoveredDanmaku.show"
      ref="menuRef"
      class="fixed bg-zinc-800/95 rounded-lg shadow-xl z-50 py-2 min-w-[140px] pointer-events-auto border border-zinc-700"
      :style="{ left: hoveredDanmaku.x + 'px', top: hoveredDanmaku.y + 'px' }"
      @mouseenter="handleMenuEnter"
      @mouseleave="startHideTimer"
    >
      <div class="px-3 py-1 text-xs text-zinc-400 border-b border-zinc-700 mb-1 truncate max-w-[140px]">
        {{ hoveredDanmaku.displayName || hoveredDanmaku.userId }}
      </div>
      <button 
        class="w-full px-4 py-1.5 text-left text-sm hover:bg-zinc-700 transition-colors text-white" 
        @click="handleHighlightUser"
      >
        高亮此人
      </button>
      <button 
        class="w-full px-4 py-1.5 text-left text-sm hover:bg-zinc-700 transition-colors text-rose-400" 
        @click="handleBlockUser"
      >
        屏蔽用户
      </button>
    </div>
  </div>
</template>