<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'

interface Props {
  videoId: string
  platform: 'youtube' | 'bilibili'
  enabled: boolean
  settings?: {
    fontSize: number
    speed: number
    opacity: number
    color: string
    strokeEnabled: boolean
    strokeColor: string
    strokeWidth: number
  }
}

const props = defineProps<Props>()

const defaultSettings = {
  fontSize: 24,
  speed: 2,
  opacity: 1,
  color: '#ffffff',
  strokeEnabled: true,
  strokeColor: '#000000',
  strokeWidth: 2
}

const settings = ref({ ...defaultSettings })

watch(() => props.settings, (newSettings) => {
  if (newSettings) {
    Object.assign(settings.value, newSettings)
  }
}, { immediate: true, deep: true })

interface DanmakuMessage {
  messageId?: string
  user_display_name?: string
  userId?: string
  comment: string
  message_type?: string
  sticker_url?: string
}

const canvasRef = ref<HTMLCanvasElement | null>(null)
const hitLayerRef = ref<HTMLDivElement | null>(null)

let ctx: CanvasRenderingContext2D | null = null
let animationId: number | null = null
let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

const danmakuQueue: DanmakuMessage[] = []
const activeDanmaku: Array<{ msg: DanmakuMessage; x: number; y: number; opacity: number }> = []
const hitLayerDivs = new Map<string, HTMLDivElement>()

let lastTime = 0

const hoveredDanmaku = ref<{ show: boolean; x: number; y: number; userId: string; displayName: string }>({
  show: false, x: 0, y: 0, userId: '', displayName: ''
})

const API_BASE = import.meta.env.VITE_API_BASE || ''
const WS_BASE = import.meta.env.VITE_WS_BASE || (API_BASE ? API_BASE.replace(/^http/, 'ws').replace(/^ws:/, 'ws:') : 'ws://localhost:8000')

function connectWebSocket() {
  if (!props.videoId || props.platform !== 'youtube') return

  const wsUrl = `${WS_BASE}/ws/danmaku/${props.videoId}`
  
  try {
    ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {
      console.log(`[Danmaku] Connected to ${props.videoId}`)
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'danmaku' && data.data) {
          for (const msg of data.data) {
            if (!danmakuQueue.find(m => m.messageId === msg.messageId)) {
              danmakuQueue.push(msg)
            }
          }
        }
      } catch (e) {
        console.error('[Danmaku] Parse error:', e)
      }
    }
    
    ws.onclose = () => {
      console.log(`[Danmaku] Disconnected from ${props.videoId}`)
      reconnectTimer = setTimeout(connectWebSocket, 3000)
    }
    
    ws.onerror = (err) => {
      console.error('[Danmaku] WS error:', err)
    }
  } catch (e) {
    console.error('[Danmaku] Failed to connect:', e)
  }
}

function disconnectWebSocket() {
  if (ws) {
    ws.close()
    ws = null
  }
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
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

  const { fontSize, speed, opacity, color, strokeEnabled, strokeColor, strokeWidth } = settings.value

  // Update active danmaku positions with time-based movement
  for (let i = activeDanmaku.length - 1; i >= 0; i--) {
    const danmaku = activeDanmaku[i]
    danmaku.x -= speed * deltaTime

    if (danmaku.x + ctx!.measureText(danmaku.msg.comment).width < 0) {
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

  // Add new danmaku from queue
  while (danmakuQueue.length > 0 && activeDanmaku.length < 20) {
    const msg = danmakuQueue.shift()!
    const y = Math.random() * (height - fontSize - 20) + fontSize + 10
    
    activeDanmaku.push({
      msg,
      x: width,
      y,
      opacity: 1
    })

    // Create hit-layer div
    if (msg.messageId && hitLayerRef.value) {
      const div = document.createElement('div')
      div.className = 'danmaku-hit-div'
      div.textContent = msg.comment
      div.dataset.messageId = msg.messageId
      div.dataset.userId = msg.userId || msg.user_display_name || ''
      div.dataset.displayName = msg.user_display_name || msg.userId || ''
      
      Object.assign(div.style, {
        position: 'absolute',
        fontSize: `${fontSize}px`,
        color: color,
        whiteSpace: 'nowrap',
        pointerEvents: 'auto',
        cursor: 'pointer',
        left: `${width}px`,
        top: `${y - fontSize}px`,
        fontFamily: 'system-ui, sans-serif',
        textShadow: strokeEnabled 
          ? `${strokeWidth}px ${strokeWidth}px 0 ${strokeColor}, -${strokeWidth}px -${strokeWidth}px 0 ${strokeColor}, ${strokeWidth}px -${strokeWidth}px 0 ${strokeColor}, -${strokeWidth}px ${strokeWidth}px 0 ${strokeColor}`
          : 'none'
      })

      div.addEventListener('mouseenter', () => {
        const rect = div.getBoundingClientRect()
        hoveredDanmaku.value = {
          show: true,
          x: rect.left,
          y: rect.top,
          userId: div.dataset.userId || '',
          displayName: div.dataset.displayName || ''
        }
      })

      div.addEventListener('mouseleave', () => {
        hoveredDanmaku.value.show = false
      })
      
      ;(div as HTMLElement).dataset.msgPlatform = props.platform

      hitLayerRef.value.appendChild(div)
      hitLayerDivs.set(msg.messageId, div)
    }
  }

  // Update hit-layer div positions
  for (const danmaku of activeDanmaku) {
    if (danmaku.msg.messageId) {
      const div = hitLayerDivs.get(danmaku.msg.messageId)
      if (div) {
        div.style.left = `${danmaku.x}px`
        div.style.top = `${danmaku.y - fontSize}px`
      }
    }
  }

  // Render to canvas
  ctx.globalAlpha = opacity
  for (const danmaku of activeDanmaku) {
    const text = danmaku.msg.comment
    const x = danmaku.x
    const y = danmaku.y

    if (strokeEnabled) {
      ctx!.strokeStyle = strokeColor
      ctx!.lineWidth = strokeWidth
      ctx!.strokeText(text, x, y)
    }
    ctx!.fillStyle = color
    ctx!.fillText(text, x, y)
  }
  ctx.globalAlpha = 1

  animationId = requestAnimationFrame(render)
}

function resizeCanvas() {
  if (!canvasRef.value) return
  const parent = canvasRef.value.parentElement
  if (!parent) return
  
  canvasRef.value.width = parent.clientWidth
  canvasRef.value.height = parent.clientHeight
}

onMounted(() => {
  if (canvasRef.value) {
    ctx = canvasRef.value.getContext('2d')
    resizeCanvas()
    lastTime = 0
    
    window.addEventListener('resize', resizeCanvas)
    animationId = requestAnimationFrame(render)
    
    if (props.enabled && props.platform === 'youtube') {
      connectWebSocket()
    }
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCanvas)
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
  disconnectWebSocket()
  hitLayerDivs.clear()
})

watch(() => props.enabled, (newVal) => {
  if (newVal && props.platform === 'youtube') {
    connectWebSocket()
  } else {
    disconnectWebSocket()
    activeDanmaku.length = 0
    danmakuQueue.length = 0
    hitLayerDivs.forEach(div => div.remove())
    hitLayerDivs.clear()
  }
})

watch(() => props.videoId, () => {
  disconnectWebSocket()
  activeDanmaku.length = 0
  danmakuQueue.length = 0
  hitLayerDivs.forEach(div => div.remove())
  hitLayerDivs.clear()
  
  if (props.enabled && props.platform === 'youtube') {
    nextTick(connectWebSocket)
  }
})
</script>

<template>
  <div v-if="enabled" class="absolute inset-0 overflow-hidden pointer-events-none">
    <canvas
      ref="canvasRef"
      class="absolute inset-0 w-full h-full"
      style="pointer-events: none;"
    />
    <div
      ref="hitLayerRef"
      class="absolute inset-0"
      style="pointer-events: none;"
    />
    
    <!-- Hover menu -->
    <div
      v-if="hoveredDanmaku.show"
      class="fixed bg-gray-800/90 rounded-lg shadow-xl z-50 py-2 min-w-[140px] pointer-events-auto"
      :style="{ left: hoveredDanmaku.x + 'px', top: (hoveredDanmaku.y + 20) + 'px' }"
    >
      <div class="px-3 py-1 text-xs text-gray-400 border-b border-gray-700 mb-1">
        {{ hoveredDanmaku.displayName || hoveredDanmaku.userId }}
      </div>
      <button class="w-full px-4 py-2 text-left text-sm hover:bg-gray-700">Highlight</button>
      <button class="w-full px-4 py-2 text-left text-sm hover:bg-gray-700 text-red-400">Block</button>
    </div>
  </div>
</template>

<style scoped>
.danmaku-hit-div {
  transition: transform 0.016s linear;
}
</style>
