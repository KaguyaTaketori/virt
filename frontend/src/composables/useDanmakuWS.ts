import { ref, watch, onMounted, onUnmounted, type Ref } from 'vue'

export interface DanmakuMessage {
  messageId?: string
  message_id?: string
  userId?: string
  user_id?: string
  user_display_name?: string
  comment: string
  message?: string
  message_type?: string
  sticker_url?: string
}

const WS_BASE =
  (import.meta.env.VITE_WS_BASE as string | undefined) ||
  ((import.meta.env.VITE_API_BASE as string | undefined)?.replace(/^http/, 'ws') ?? 'ws://localhost:8000')

export function useDanmakuWS(
  videoId: Ref<string>,
  platform: Ref<string>,
  enabled: Ref<boolean>,
) {
  const queue: DanmakuMessage[] = []

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectAttempts = 0
  const MAX_BACKOFF = 30_000

  function connect() {
    if (videoId.value === '' || platform.value !== 'youtube') return

    try {
      ws = new WebSocket(`${WS_BASE}/ws/danmaku/${videoId.value}`)
    } catch {
      scheduleReconnect()
      return
    }

    ws.onopen = () => { reconnectAttempts = 0 }

    ws.onmessage = (event) => {
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
            if (!queue.find((m) => m.messageId === msg.messageId)) {
              queue.push(msg)
            }
          }
        }
      } catch { /* ignore parse errors */ }
    }

    ws.onerror = (err) => console.error('[WS Error]', err)
    ws.onclose = () => {
      ws = null
      if (enabled.value && platform.value === 'youtube') scheduleReconnect()
    }
  }

  function disconnect() {
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
    if (ws) { ws.onclose = null; ws.close(); ws = null }
    reconnectAttempts = 0
  }

  function scheduleReconnect() {
    const delay = Math.min(1_000 * 2 ** reconnectAttempts, MAX_BACKOFF)
    reconnectAttempts++
    reconnectTimer = setTimeout(connect, delay)
  }

  function drainQueue(): DanmakuMessage[] {
    return queue.splice(0, queue.length)
  }

  watch(enabled, (val) => {
    if (val && platform.value === 'youtube') connect()
    else disconnect()
  })

  watch(videoId, () => {
    disconnect()
    queue.length = 0
    if (enabled.value && platform.value === 'youtube') connect()
  })

  onMounted(() => {
    if (enabled.value && platform.value === 'youtube') connect()
  })

  onUnmounted(() => {
    disconnect()
    queue.length = 0
  })

  return { queue, drainQueue, connect, disconnect }
}

export function useDanmakuHitLayer(
  hitLayerRef: Ref<HTMLDivElement | null>,
) {
  const hitLayerDivs = new Map<string, HTMLDivElement>()

  function addGhostDiv(
    messageId: string,
    text: string,
    x: number,
    y: number,
    textWidth: number,
    fontSize: number,
  ) {
    if (!hitLayerRef.value || !messageId) return

    const div = document.createElement('div')
    div.className = 'danmaku-ghost absolute cursor-pointer whitespace-nowrap'
    div.textContent = text
    div.dataset.messageId = messageId

    Object.assign(div.style, {
      top: '0px',
      left: '0px',
      width: `${textWidth}px`,
      height: `${fontSize}px`,
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