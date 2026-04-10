import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useWebSocket } from '@vueuse/core'
import type { Ref, ComputedRef } from 'vue'
import type { DanmakuMessage } from '@/types/danmaku'

export interface DanmakuState {
  messages: Ref<DanmakuMessage[]>
  connected: ComputedRef<boolean>
  loading: Ref<boolean>
  error: Ref<Error | null>
}

export interface DanmakuOptions {
  videoId: string
  autoReconnect?: boolean
  maxMessages?: number
}

export function useDanmaku(options: DanmakuOptions) {
  const {
    videoId,
    autoReconnect = true,
    maxMessages = 500,
  } = options

  const messages = ref<DanmakuMessage[]>([])
  const loading = ref(false)
  const error = ref<Error | null>(null)

  const wsUrl = computed(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}/api/ws/danmaku/${videoId}`
  })

  const { data, send, open, close, isOpen, status } = useWebSocket(wsUrl.value, {
    autoReconnect,
    reconnected: {
      retries: 3,
      delay: 1000,
    },
    onMessage(_ws, event) {
      try {
        const msg = JSON.parse(event.data) as DanmakuMessage
        messages.value.push(msg)
        if (messages.value.length > maxMessages) {
          messages.value = messages.value.slice(-maxMessages)
        }
      } catch (e) {
        console.error('[Danmaku] Parse error:', e)
      }
    },
    onError(_ws, event) {
      error.value = new Error(event.type)
      console.error('[Danmaku] Error:', event)
    },
    onConnected(_ws) {
      loading.value = false
      error.value = null
    },
    onDisconnected(_ws) {
      loading.value = false
    },
  })

  const connected = computed(() => status.value === 'OPEN')

  function sendMessage(text: string, color?: string) {
    if (!connected.value) return
    send(JSON.stringify({ text, color: color || '#ffffff' }))
  }

  function clearMessages() {
    messages.value = []
  }

  return {
    messages,
    connected,
    loading,
    error,
    sendMessage,
    clearMessages,
    open,
    close,
  }
}

export function useDanmakuRenderer(
  canvasRef: Ref<HTMLCanvasElement | null>,
  messages: Ref<DanmakuMessage[]>,
  options?: {
    speed?: number
    fontSize?: number
    opacity?: number
  },
) {
  const {
    speed = 2,
    fontSize = 24,
    opacity = 1,
  } = options || {}

  let animationFrameId: number | null = null
  const canvas = computed(() => canvasRef.value)
  const ctx = computed(() => canvas.value?.getContext('2d'))

  function render() {
    const cvs = canvas.value
    const context = ctx.value
    if (!cvs || !context) return

    context.clearRect(0, 0, cvs.width, cvs.height)
    context.globalAlpha = opacity

    const now = Date.now()
    for (const msg of messages.value) {
      const x = cvs.width - ((now - msg.timestamp) / 1000) * speed * 50
      if (x < -100) continue

      context.font = `${fontSize}px sans-serif`
      context.fillStyle = msg.color || '#ffffff'
      context.fillText(msg.text, x, cvs.height / 2)
    }

    animationFrameId = requestAnimationFrame(render)
  }

  function start() {
    if (animationFrameId) return
    render()
  }

  function stop() {
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId)
      animationFrameId = null
    }
  }

  onMounted(() => start())
  onUnmounted(() => stop())

  return { start, stop }
}