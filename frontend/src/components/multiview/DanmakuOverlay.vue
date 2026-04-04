<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { DEFAULT_DANMAKU_SETTINGS, type DanmakuSettings } from '@/types/danmaku'
 import { useDanmakuUsers } from '@/composables/useDanmakuUsers'

const { blockUser, highlightUser, isBlocked } = useDanmakuUsers()

interface Props {
  videoId: string
  platform: 'youtube' | 'bilibili'
  enabled: boolean
  settings?: DanmakuSettings
}

interface ActiveDanmaku {
  msg: {
    messageId?: string
    user_display_name?: string
    userId?: string
    comment: string
    message_type?: string
    sticker_url?: string
  }
  x: number
  y: number
  opacity: number
  textWidth: number
  isHovered: boolean 
}

const props = defineProps<Props>()

const settings = ref<DanmakuSettings>({ ...DEFAULT_DANMAKU_SETTINGS })

watch(() => props.settings, (s) => {
  if (s) {
    Object.assign(settings.value, s)
    applyCanvasFont()
    for (const d of activeDanmaku) {
      d.textWidth = ctx?.measureText(d.msg.comment).width ?? d.textWidth
    }
  }
}, { deep: true })

const canvasRef = ref<HTMLCanvasElement | null>(null)
const hitLayerRef = ref<HTMLDivElement | null>(null)

let ctx: CanvasRenderingContext2D | null = null
let animationId: number | null = null
let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

const danmakuQueue: ActiveDanmaku['msg'][] = []
const activeDanmaku: ActiveDanmaku[] = []
const hitLayerDivs = new Map<string, HTMLDivElement>()

let lastTime = 0

// 悬浮菜单状态
const hoveredDanmaku = ref<{ show: boolean; x: number; y: number; userId: string; displayName: string, messageId: string }>({
  show: false, x: 0, y: 0, userId: '', displayName: '', messageId: ''
})

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

  const canvas = canvasRef.value
  const { width, height } = canvas

  ctx.clearRect(0, 0, width, height)

  const { speed, opacity, color, strokeEnabled, strokeColor, strokeWidth, fontSize } = settings.value

  // 1. 更新弹幕位置
  for (let i = activeDanmaku.length - 1; i >= 0; i--) {
    const danmaku = activeDanmaku[i]
    
    if (!danmaku.isHovered) {
      danmaku.x -= speed * deltaTime
    }

    if (danmaku.x + danmaku.textWidth < 0) {
      activeDanmaku.splice(i, 1)
      if (danmaku.msg.messageId) {
        const div = hitLayerDivs.get(danmaku.msg.messageId)
        if (div) {
          div.remove()
          hitLayerDivs.delete(danmaku.msg.messageId)
        }
      }
    }
  }

  while (danmakuQueue.length > 0 && activeDanmaku.length < 30) {
    const msg = danmakuQueue.shift()!
    if (msg.userId && isBlocked(msg.userId)) continue
    const textWidth = ctx.measureText(msg.comment).width
    const y = Math.random() * (height - fontSize - 10)

    activeDanmaku.push({ msg, x: width, y, opacity: 1, textWidth, isHovered: false })

    if (msg.messageId && hitLayerRef.value) {
      const div = document.createElement('div')
      div.className = 'danmaku-ghost absolute cursor-pointer whitespace-nowrap'
      div.textContent = msg.comment
      div.dataset.messageId = msg.messageId
      div.dataset.userId = msg.userId || msg.user_display_name || ''
      div.dataset.displayName = msg.user_display_name || msg.userId || ''
      
      Object.assign(div.style, {
        top: '0px',
        left: '0px',
        width: `${textWidth}px`,
        height: `${fontSize}px`,
        lineHeight: `${fontSize}px`,
        fontSize: `${fontSize}px`,
        color: 'transparent',
        userSelect: 'none',
        pointerEvents: 'auto', 
        transform: `translate3d(${width}px, ${y}px, 0)` 
      })

      hitLayerRef.value.appendChild(div)
      hitLayerDivs.set(msg.messageId, div)
    }
  }

  ctx.globalAlpha = opacity
  for (const danmaku of activeDanmaku) {
    const { comment, messageId } = danmaku.msg
    const { x, y } = danmaku

    if (messageId) {
      const div = hitLayerDivs.get(messageId)
      if (div) {
        div.style.transform = `translate3d(${x}px, ${y}px, 0)`
      }
    }

    if (strokeEnabled) {
      ctx.strokeStyle = strokeColor
      ctx.lineWidth = strokeWidth
      ctx.strokeText(comment, x, y)
    }
    ctx.fillStyle = color
    ctx.fillText(comment, x, y)
  }
  ctx.globalAlpha = 1

  animationId = requestAnimationFrame(render)
}

let hideMenuTimer: ReturnType<typeof setTimeout> | null = null

function handleMenuEnter() {
  if (hideMenuTimer) {
    clearTimeout(hideMenuTimer)
    hideMenuTimer = null
  }
  const d = activeDanmaku.find(d => d.msg.messageId === hoveredDanmaku.value.messageId)
  if (d) d.isHovered = true
}

function handleMenuLeave() {
  hideMenuTimer = setTimeout(() => {
    hoveredDanmaku.value.show = false
    const d = activeDanmaku.find(d => d.msg.messageId === hoveredDanmaku.value.messageId)
    if (d) d.isHovered = false
  }, 250)
}

function setupHitLayerEvents() {
  if (!hitLayerRef.value) return

  hitLayerRef.value.addEventListener('mouseover', (e) => {
    const target = e.target as HTMLElement
    if (target.classList.contains('danmaku-ghost')) {
      const msgId = target.dataset.messageId
      
      if (hideMenuTimer) {
        clearTimeout(hideMenuTimer)
        hideMenuTimer = null
      }

      if (hoveredDanmaku.value.show && hoveredDanmaku.value.messageId !== msgId) {
        const prev = activeDanmaku.find(d => d.msg.messageId === hoveredDanmaku.value.messageId)
        if (prev) prev.isHovered = false
      }

      const danmaku = activeDanmaku.find(d => d.msg.messageId === msgId)
      if (danmaku) {
        danmaku.isHovered = true
        const rect = target.getBoundingClientRect()
        hoveredDanmaku.value = {
          show: true,
          x: rect.left,
          y: rect.bottom,
          userId: target.dataset.userId || '',
          displayName: target.dataset.displayName || '',
          messageId: msgId || ''
        }
      }
    }
  })

  hitLayerRef.value.addEventListener('mouseout', (e) => {
    const target = e.target as HTMLElement
    if (target.classList.contains('danmaku-ghost')) {
      const msgId = target.dataset.messageId
      
      hideMenuTimer = setTimeout(() => {
        const danmaku = activeDanmaku.find(d => d.msg.messageId === msgId)
        if (danmaku) danmaku.isHovered = false
        
        if (hoveredDanmaku.value.messageId === msgId) {
          hoveredDanmaku.value.show = false
        }
      }, 250)
    }
  })
}

const WS_BASE =
  import.meta.env.VITE_WS_BASE ||
  (import.meta.env.VITE_API_BASE?.replace(/^http/, 'ws') ?? 'ws://localhost:8000')

let reconnectAttempts = 0
const MAX_BACKOFF = 30_000

function connectWebSocket() {
  if (!props.videoId || props.platform !== 'youtube') return

  const url = `${WS_BASE}/ws/danmaku/${props.videoId}`
  try {
    ws = new WebSocket(url)
  } catch (e) {
    scheduleReconnect()
    return
  }

  ws.onopen = () => {
    reconnectAttempts = 0
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'danmaku' && Array.isArray(data.data)) {
        for (const rawMsg of data.data) {
          const msg = {
            ...rawMsg,
            messageId: rawMsg.message_id || rawMsg.messageId
              || `local_${Date.now()}_${Math.random().toString(36).slice(2)}`,
            userId: rawMsg.user_id || rawMsg.userId,
            comment: rawMsg.comment || rawMsg.message || '',
          }
          if (!danmakuQueue.find(m => m.messageId === msg.messageId))
            danmakuQueue.push(msg)
        }
      }
    } catch { /* ignore parse errors */ }
  }

  ws.onerror  = (err) => console.error('[WS Error] 连接发生错误:', err)

  ws.onclose = () => {
    ws = null
    if (props.enabled && props.platform === 'youtube') scheduleReconnect()
  }
}

function scheduleReconnect() {
  const delay = Math.min(1_000 * 2 ** reconnectAttempts, MAX_BACKOFF)
  reconnectAttempts++
  reconnectTimer = setTimeout(connectWebSocket, delay)
}

function disconnectWebSocket() {
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
  if (ws) { ws.onclose = null; ws.close(); ws = null }
  reconnectAttempts = 0
}

function clearDanmaku() {
  activeDanmaku.length = 0
  danmakuQueue.length  = 0
  hitLayerDivs.forEach((d) => d.remove())
  hitLayerDivs.clear()
}

function closeHoverMenu() {
  hoveredDanmaku.value.show = false
  const d = activeDanmaku.find(d => d.msg.messageId === hoveredDanmaku.value.messageId)
  if (d) d.isHovered = false
}

function handleHighlightUser() {
  if (!hoveredDanmaku.value.userId) return
  highlightUser(hoveredDanmaku.value.userId)
  closeHoverMenu()
}

function handleBlockUser() {
  if (!hoveredDanmaku.value.userId) return
  blockUser(hoveredDanmaku.value.userId)
  for (let i = activeDanmaku.length - 1; i >= 0; i--) {
    if (activeDanmaku[i].msg.userId === hoveredDanmaku.value.userId) {
      const mid = activeDanmaku[i].msg.messageId
      if (mid) {
        hitLayerDivs.get(mid)?.remove()
        hitLayerDivs.delete(mid)
      }
      activeDanmaku.splice(i, 1)
    }
  }
  
  closeHoverMenu()
}

onMounted(() => {
  if (canvasRef.value) {
    ctx = canvasRef.value.getContext('2d')
    resizeCanvas()
    window.addEventListener('resize', resizeCanvas)
    setupHitLayerEvents()
    animationId = requestAnimationFrame(render)
    if (props.enabled && props.platform === 'youtube') connectWebSocket()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCanvas)
  if (animationId) cancelAnimationFrame(animationId)
  if (hideMenuTimer) clearTimeout(hideMenuTimer)
  disconnectWebSocket()
  hitLayerDivs.clear()
})

watch(() => props.enabled, (newVal) => {
  if (newVal && props.platform === 'youtube') connectWebSocket()
  else { disconnectWebSocket(); clearDanmaku() }
})

watch(() => props.videoId, () => {
  disconnectWebSocket(); clearDanmaku()
  if (props.enabled && props.platform === 'youtube') nextTick(connectWebSocket)
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