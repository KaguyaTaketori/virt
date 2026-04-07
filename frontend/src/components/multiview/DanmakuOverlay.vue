<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, toRef } from 'vue'
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

const { blockUser, highlightUser, isBlocked } = useDanmakuUsers()

const { drainQueue, disconnect } = useDanmakuWS(
  toRef(props, 'videoId'),
  toRef(props, 'platform'),
  toRef(props, 'enabled')
)

const hitLayerRef = ref<HTMLDivElement | null>(null)
const { 
  addGhostDiv, 
  removeGhostDiv, 
  clearAll: clearHitLayer, 
  updatePosition 
} = useDanmakuHitLayer(hitLayerRef)

const settings = ref<DanmakuSettings>({ ...DEFAULT_DANMAKU_SETTINGS })
const canvasRef = ref<HTMLCanvasElement | null>(null)
let ctx: CanvasRenderingContext2D | null = null
let animationId: number | null = null
let lastTime = 0

const activeDanmaku = ref<ActiveDanmaku[]>([])

const hoveredDanmaku = ref<{ show: boolean; x: number; y: number; userId: string; displayName: string, messageId: string }>({
  show: false, x: 0, y: 0, userId: '', displayName: '', messageId: ''
})
let hideMenuTimer: ReturnType<typeof setTimeout> | null = null

function applyCanvasFont() {
  if (!ctx) return
  const { fontSize } = settings.value
  ctx.font = `bold ${fontSize}px system-ui, sans-serif`
  ctx.textBaseline = 'top' 
}

function resizeCanvas() {
  if (!canvasRef.value) return
  const parent = canvasRef.value.parentElement
  if (!parent) return
  
  canvasRef.value.width = parent.clientWidth
  canvasRef.value.height = parent.clientHeight
  applyCanvasFont()
}

function render(timestamp: number) {
  if (!ctx || !canvasRef.value || !props.enabled) {
    animationId = requestAnimationFrame(render)
    return
  }

  const deltaTime = lastTime ? (timestamp - lastTime) / 16.67 : 1
  lastTime = timestamp

  const { width, height } = canvasRef.value

  ctx.clearRect(0, 0, width, height)

  const { speed, opacity, color, strokeEnabled, strokeColor, strokeWidth, fontSize } = settings.value

  // 1. 更新弹幕位置
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
    const textWidth = ctx.measureText(msg.comment).width
    const y = Math.random() * (height - fontSize - 20) + 10

    activeDanmaku.value.push({
      msg,
      x: width,
      y,
      opacity: 1,
      textWidth,
      isHovered: false
    })

    addGhostDiv(mId, msg.comment, width, y, textWidth, fontSize, msg.userId, msg.user_display_name)
  }

  ctx.globalAlpha = opacity
  for (const danmaku of activeDanmaku.value) {
    if (strokeEnabled) {
      ctx.strokeStyle = strokeColor
      ctx.lineWidth = strokeWidth
      ctx.strokeText(danmaku.msg.comment, danmaku.x, danmaku.y)
    }
    ctx.fillStyle = color
    ctx.fillText(danmaku.msg.comment, danmaku.x, danmaku.y)
  }
  ctx.globalAlpha = 1

  animationId = requestAnimationFrame(render)
}

function handleMenuEnter() {
  if (hideMenuTimer) {
    clearTimeout(hideMenuTimer)
    hideMenuTimer = null
  }
  const d = activeDanmaku.value.find(d => d.msg.messageId === hoveredDanmaku.value.messageId)
  if (d) d.isHovered = true
}

function handleMenuLeave() {
  hideMenuTimer = setTimeout(() => {
    hoveredDanmaku.value.show = false
    const d = activeDanmaku.value.find(d => d.msg.messageId === hoveredDanmaku.value.messageId)
    if (d) d.isHovered = false
  }, 250)
}

function setupHitLayerEvents() {
  if (!hitLayerRef.value) return

  hitLayerRef.value.addEventListener('mouseover', (e) => {
    const target = e.target as HTMLElement
    if (target.classList.contains('danmaku-ghost')) {
      const msgId = target.dataset.messageId
      if (!msgId) return

      if (hideMenuTimer) { clearTimeout(hideMenuTimer); hideMenuTimer = null }

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

  hitLayerRef.value.addEventListener('mouseout', (e) => {
    const target = e.target as HTMLElement
    if (target.classList.contains('danmaku-ghost')) {
      handleMenuLeave()
    }
  })
}

function handleBlockUser() {
  if (!hoveredDanmaku.value.userId) return
  blockUser(hoveredDanmaku.value.userId)
  
  for (let i = activeDanmaku.value.length - 1; i >= 0; i--) {
    if (activeDanmaku.value[i].msg.userId === hoveredDanmaku.value.userId) {
      removeGhostDiv(activeDanmaku.value[i].msg.messageId)
      activeDanmaku.value.splice(i, 1)
    }
  }
  hoveredDanmaku.value.show = false
}

function handleHighlightUser() {
  if (!hoveredDanmaku.value.userId) return
  highlightUser(hoveredDanmaku.value.userId)
  hoveredDanmaku.value.show = false
}

function clearAll() {
  activeDanmaku.value = []
  clearHitLayer()
}

onMounted(() => {
  if (canvasRef.value) {
    ctx = canvasRef.value.getContext('2d')
    resizeCanvas()
    window.addEventListener('resize', resizeCanvas)
    setupHitLayerEvents()
    animationId = requestAnimationFrame(render)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCanvas)
  if (animationId) cancelAnimationFrame(animationId)
  disconnect()
  clearAll()
})

watch(() => props.settings, (s) => {
  if (s) {
    Object.assign(settings.value, s)
    applyCanvasFont()
  }
}, { deep: true })

watch(() => props.videoId, () => {
  clearAll()
})

watch(() => props.enabled, (val) => {
  if (!val) clearAll()
})
</script>

<template>
  <div v-if="enabled" class="absolute inset-0 overflow-hidden pointer-events-none z-20">
    <canvas
      ref="canvasRef"
      class="absolute inset-0 w-full h-full pointer-events-none"
    />
    
    <div ref="hitLayerRef" class="absolute inset-0 pointer-events-none" />
    
    <div
      v-if="hoveredDanmaku.show"
      class="fixed bg-zinc-800/95 rounded-lg shadow-xl z-50 py-2 min-w-[140px] pointer-events-auto border border-zinc-700"
      :style="{ left: hoveredDanmaku.x + 'px', top: hoveredDanmaku.y + 'px' }"
      @mouseenter="handleMenuEnter"
      @mouseleave="handleMenuLeave"
    >
      <div class="px-3 py-1 text-xs text-zinc-400 border-b border-zinc-700 mb-1 truncate max-w-[140px]">
        {{ hoveredDanmaku.displayName || hoveredDanmaku.userId }}
      </div>
      <button class="w-full px-4 py-1.5 text-left text-sm hover:bg-zinc-700 transition-colors text-white" @click="handleHighlightUser">高亮此人</button>
      <button class="w-full px-4 py-1.5 text-left text-sm hover:bg-zinc-700 transition-colors text-rose-400" @click="handleBlockUser">屏蔽用户</button>
    </div>
  </div>
</template>