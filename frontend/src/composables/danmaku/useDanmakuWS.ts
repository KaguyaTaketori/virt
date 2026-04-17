import { ref, watch, toValue, type MaybeRefOrGetter, computed } from 'vue'
import { useWebSocket } from '@vueuse/core'
import { DanmakuMessage } from '@/types/danmaku'

const WS_BASE =
  (import.meta.env.VITE_WS_BASE as string | undefined) ||
  ((import.meta.env.VITE_API_BASE as string | undefined)?.replace(/^http/, 'ws') ?? 'ws://localhost:8000')

export function useDanmakuWS(
  videoId: MaybeRefOrGetter<string | undefined>,
  platform: MaybeRefOrGetter<string | undefined>,
  enabled: MaybeRefOrGetter<boolean>,
) {
  const queue = ref<DanmakuMessage[]>([])
  const url = ref<string>('')

  const { status, close, open } = useWebSocket(url, {
    autoReconnect: {
      retries: () => true, 
      delay: 1000,
      onFailed() {
        console.warn('[WS] Reconnection failed')
      },
    },
    onMessage(_ws, event) {
      try {
        const data = JSON.parse(event.data as string)
        if (data.type === 'danmaku' && Array.isArray(data.data)) {
          for (const raw of data.data) {
            const msg: DanmakuMessage = {
              ...raw,
              messageId: raw.message_id ?? raw.messageId ??
                `local_${Date.now()}_${Math.random().toString(36).slice(2)}`,
              userId: raw.user_id ?? raw.userId,
              comment: raw.comment ?? raw.message ?? '',
            }
            if (!queue.value.some((m) => m.messageId === msg.messageId)) {
              queue.value.push(msg)
            }
          }
        }
      } catch { /* ignore parse errors */ }
    },
    immediate: false,
  })

  const isConnected = computed(() => status.value === 'OPEN')

  function connect() {
    const vid = toValue(videoId)
    const plat = toValue(platform)
    if (!vid || plat !== 'youtube') return

    const newUrl = `${WS_BASE}/ws/danmaku/${vid}`
    if (url.value !== newUrl) {
      url.value = newUrl
      open()
    }
  }

  function disconnect() {
    close()
    queue.value = []
  }

  function drainQueue(): DanmakuMessage[] {
    if (queue.value.length === 0) return []
    return queue.value.splice(0, queue.value.length)
  }

  watch(
    [() => toValue(enabled), () => toValue(platform), () => toValue(videoId)],
    ([en, plat, vid]) => {
      if (en && plat === 'youtube' && vid) {
        url.value = `${WS_BASE}/ws/danmaku/${vid}`
        open()
      } else {
        disconnect()
      }
    },
    { immediate: true }
  )

  return { 
    queue, 
    drainQueue, 
    connect, 
    disconnect,
    isConnected,
    status
  }
}

export function useDanmakuHitLayer(
  hitLayerRef: { value: HTMLDivElement | null },
) {
  const hitLayerDivs = new Map<string, HTMLDivElement>()

  function addGhostDiv(
    messageId: string,
    text: string,
    x: number,
    y: number,
    textWidth: number,
    fontSize: number,
    userId?: string,
    displayName?: string 
  ) {
    if (!hitLayerRef.value || !messageId) return

    const div = document.createElement('div')
    div.className = 'danmaku-ghost absolute cursor-pointer whitespace-nowrap'
    div.textContent = text
    div.dataset.messageId = messageId
    if (userId) div.dataset.userId = userId
    if (displayName) div.dataset.displayName = displayName

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
      transform: `translate3d(${x}px, ${y}px, 0)`,
    })

    hitLayerRef.value.appendChild(div)
    hitLayerDivs.set(messageId, div)
  }

  function removeGhostDiv(messageId: string) {
    const div = hitLayerDivs.get(messageId)
    if (div) {
      div.remove()
      hitLayerDivs.delete(messageId)
    }
  }

  function clearAll() {
    hitLayerDivs.forEach((div) => div.remove())
    hitLayerDivs.clear()
  }

  function updatePosition(messageId: string, x: number, y: number) {
    const div = hitLayerDivs.get(messageId)
    if (div) div.style.transform = `translate3d(${x}px, ${y}px, 0)`
  }

  return { hitLayerDivs, addGhostDiv, removeGhostDiv, clearAll, updatePosition }
}