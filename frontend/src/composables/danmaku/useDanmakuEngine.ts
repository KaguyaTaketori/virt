import { ref, computed, watch, type Ref } from 'vue'
import { useRafFn, useTimeoutFn } from '@vueuse/core'
import { type DanmakuSettings, type ActiveDanmaku } from '@/types/danmaku'
import { useDanmakuUsers } from './useDanmakuUsers'
import { useDanmakuWS, useDanmakuHitLayer } from './useDanmakuWS'

interface EngineOptions {
  videoId: Ref<string>
  platform: Ref<'youtube' | 'bilibili'>
  enabled: Ref<boolean>
  settings: Ref<DanmakuSettings>
  width: Ref<number>
  height: Ref<number>
  hitLayerRef: Ref<HTMLDivElement | null>
  canvasRef: Ref<HTMLCanvasElement | null>
}

export function useDanmakuEngine(options: EngineOptions) {
  const { videoId, platform, enabled, settings, width, height, hitLayerRef, canvasRef } = options

  // --- 常量 ---
  const TRACK_GAP = 40
  const MAX_PAUSE_TIME = 5000

  // --- 状态 ---
  const activeDanmaku = ref<ActiveDanmaku[]>([])
  const hoveredDanmaku = ref({
    show: false, x: 0, y: 0, userId: '', displayName: '', messageId: ''
  })

  // --- 依赖 Composables ---
  const { blockUser, highlightUser, isBlocked } = useDanmakuUsers()
  const { drainQueue, disconnect } = useDanmakuWS(videoId, platform, enabled)
  const { addGhostDiv, removeGhostDiv, clearAll: clearHitLayer, updatePosition } = useDanmakuHitLayer(hitLayerRef)

  // --- 轨道计算 ---
  const trackCount = computed(() => {
    const lineHeight = settings.value.fontSize + 12
    const count = Math.floor((height.value - 20) / lineHeight)
    return Math.max(1, count)
  })

  function findAvailableTrack(): number {
    const count = trackCount.value
    const lineHeight = settings.value.fontSize + 12
    const startTrack = Math.floor(Math.random() * count)

    for (let i = 0; i < count; i++) {
      const trackIndex = (startTrack + i) % count
      const trackY = trackIndex * lineHeight + 10
      const danmakusInTrack = activeDanmaku.value.filter(d => d.y === trackY)

      if (danmakusInTrack.length === 0) return trackIndex

      const lastDanmaku = danmakusInTrack.reduce((prev, curr) => prev.x > curr.x ? prev : curr)
      const isLastStopped = hoveredDanmaku.value.show && hoveredDanmaku.value.messageId === lastDanmaku.msg.messageId
      const lastEdgeX = lastDanmaku.x + lastDanmaku.textWidth

      if (lastEdgeX < width.value - TRACK_GAP && !isLastStopped) {
        return trackIndex
      }
    }
    return -1
  }

  // --- 交互计时器 ---
  const { start: startHideTimer, stop: stopHideTimer } = useTimeoutFn(() => resumeMovement(), 250, { immediate: false })
  const { start: startForceResumeTimer, stop: stopForceResumeTimer } = useTimeoutFn(() => resumeMovement(), MAX_PAUSE_TIME, { immediate: false })

  function resumeMovement() {
    hoveredDanmaku.value.show = false
    hoveredDanmaku.value.messageId = ''
    stopForceResumeTimer()
  }

  // --- 渲染逻辑 ---
  let ctx: CanvasRenderingContext2D | null = null

  const applyCanvasFont = () => {
    if (!canvasRef.value) return
    ctx = canvasRef.value.getContext('2d')
    if (!ctx) return
    ctx.font = `bold ${settings.value.fontSize}px system-ui, -apple-system, sans-serif`
    ctx.textBaseline = 'top'
  }

  function drawDanmaku(d: ActiveDanmaku) {
    if (!ctx) return
    const { color, strokeEnabled, strokeColor, strokeWidth } = settings.value
    if (strokeEnabled) {
      ctx.strokeStyle = strokeColor
      ctx.lineWidth = strokeWidth
      ctx.strokeText(d.msg.comment, d.x, d.y)
    }
    ctx.fillStyle = color
    ctx.fillText(d.msg.comment, d.x, d.y)
  }

  // --- 动画循环 ---
  const { pause, resume } = useRafFn(({ delta }) => {
    if (!ctx || !enabled.value) return

    ctx.clearRect(0, 0, width.value, height.value)
    const deltaTime = delta / 16.67
    const { speed, opacity, fontSize } = settings.value

    ctx.globalAlpha = opacity
    for (let i = activeDanmaku.value.length - 1; i >= 0; i--) {
      const d = activeDanmaku.value[i]
      const isCurrentlyHovered = hoveredDanmaku.value.show && hoveredDanmaku.value.messageId === d.msg.messageId

      if (!isCurrentlyHovered) {
        d.x -= speed * deltaTime
      }

      if (d.x + d.textWidth < 0) {
        removeGhostDiv(d.msg.messageId)
        activeDanmaku.value.splice(i, 1)
        continue
      }

      updatePosition(d.msg.messageId, d.x, d.y)
      drawDanmaku(d)
    }
    ctx.globalAlpha = 1

    // 处理新弹幕
    const newMsgs = drainQueue()
    for (const msg of newMsgs) {
      if (msg.userId && isBlocked(msg.userId)) continue
      if (activeDanmaku.value.length > 60) break

      const trackIndex = findAvailableTrack()
      if (trackIndex === -1) break

      const textWidth = ctx.measureText(msg.comment).width
      const mId = msg.messageId || `local_${Math.random().toString(36).slice(2)}`
      const y = trackIndex * (fontSize + 12) + 10

      activeDanmaku.value.push({ msg, x: width.value, y, opacity: 1, textWidth, isHovered: false })
      addGhostDiv(mId, msg.comment, width.value, y, textWidth, fontSize, msg.userId, msg.user_display_name)
    }
  })

  // --- 工具方法 ---
  function clearAll() {
    activeDanmaku.value = []
    clearHitLayer()
    resumeMovement()
  }

  function handleBlockUser() {
    const uid = hoveredDanmaku.value.userId
    if (!uid) return
    blockUser(uid)
    activeDanmaku.value = activeDanmaku.value.filter(d => {
      if (d.msg.userId === uid) {
        removeGhostDiv(d.msg.messageId)
        return false
      }
      return true
    })
    resumeMovement()
  }

  function handleHighlightUser() {
    if (hoveredDanmaku.value.userId) highlightUser(hoveredDanmaku.value.userId)
    resumeMovement()
  }

  // --- 监听器 ---
  watch([width, height], ([w, h]) => {
    if (canvasRef.value) {
      canvasRef.value.width = w
      canvasRef.value.height = h
      applyCanvasFont()
    }
  })

  return {
    activeDanmaku,
    hoveredDanmaku,
    resume,
    pause,
    clearAll,
    applyCanvasFont,
    handleBlockUser,
    handleHighlightUser,
    startHideTimer,
    stopHideTimer,
    startForceResumeTimer,
    resumeMovement,
    disconnect
  }
}