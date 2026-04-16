<script setup lang="ts">
import { ref, watch, toRef, computed, onUnmounted } from 'vue'
import { 
  useElementSize, 
  useRafFn, 
  useEventListener, 
  useTimeoutFn 
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

// --- 基础状态 ---
const containerRef = ref<HTMLDivElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const hitLayerRef = ref<HTMLDivElement | null>(null)
const { width, height } = useElementSize(containerRef)
const settings = ref<DanmakuSettings>({ ...DEFAULT_DANMAKU_SETTINGS })
const activeDanmaku = ref<ActiveDanmaku[]>([])

// --- Composables ---
const { blockUser, highlightUser, isBlocked } = useDanmakuUsers()
const { drainQueue, disconnect } = useDanmakuWS(
  toRef(props, 'videoId'),
  toRef(props, 'platform'),
  toRef(props, 'enabled')
)
const { addGhostDiv, removeGhostDiv, clearAll: clearHitLayer, updatePosition } = useDanmakuHitLayer(hitLayerRef)

// --- 轨道管理配置 ---
const TRACK_GAP = 40 // 弹幕之间的最小水平间距 (px)
const trackLastX = ref<number[]>([]) // 记录每个轨道末尾弹幕的右边缘 X 坐标

const trackCount = computed(() => {
  const lineHeight = settings.value.fontSize + 12
  const count = Math.floor((height.value - 20) / lineHeight)
  return Math.max(1, count)
})

// 当轨道数量变化（如缩屏）时，重置轨道记录
watch(trackCount, (count) => {
  trackLastX.value = new Array(count).fill(0)
}, { immediate: true })

// 寻找可用轨道
function findAvailableTrack(): number {
  const count = trackCount.value
  const indices = Array.from({ length: count }, (_, i) => i)
  
  // 随机打乱搜索顺序，避免所有弹幕都挤在顶部轨道
  const shuffled = indices.sort(() => Math.random() - 0.5)
  
  for (const i of shuffled) {
    // 如果该轨道最后一条弹幕的右边缘已经进入屏幕内并留有间距
    if (trackLastX.value[i] < width.value - TRACK_GAP) {
      return i
    }
  }
  return -1 // 所有轨道都满了
}

// --- 悬浮菜单逻辑 ---
const hoveredDanmaku = ref({ 
  show: false, x: 0, y: 0, userId: '', displayName: '', messageId: '' 
})

const { start: startHideTimer, stop: stopHideTimer } = useTimeoutFn(() => {
  hoveredDanmaku.value.show = false
  const d = activeDanmaku.value.find(d => d.msg.messageId === hoveredDanmaku.value.messageId)
  if (d) d.isHovered = false
}, 250, { immediate: false })

function handleMenuEnter() {
  stopHideTimer()
  const d = activeDanmaku.value.find(d => d.msg.messageId === hoveredDanmaku.value.messageId)
  if (d) d.isHovered = true
}

// --- Canvas 绘制核心 ---
let ctx: CanvasRenderingContext2D | null = null

const applyCanvasFont = () => {
  if (!canvasRef.value) return
  ctx = canvasRef.value.getContext('2d')
  if (!ctx) return
  const { fontSize } = settings.value
  ctx.font = `bold ${fontSize}px system-ui, -apple-system, sans-serif`
  ctx.textBaseline = 'top'
}

// 监听尺寸变化同步 Canvas 画布大小
watch([width, height], ([w, h]) => {
  if (canvasRef.value) {
    canvasRef.value.width = w
    canvasRef.value.height = h
    applyCanvasFont()
  }
})

function drawDanmaku(danmaku: ActiveDanmaku) {
  if (!ctx) return
  const { color, strokeEnabled, strokeColor, strokeWidth } = settings.value
  
  if (strokeEnabled) {
    ctx.strokeStyle = strokeColor
    ctx.lineWidth = strokeWidth
    ctx.strokeText(danmaku.msg.comment, danmaku.x, danmaku.y)
  }
  ctx.fillStyle = color
  ctx.fillText(danmaku.msg.comment, danmaku.x, danmaku.y)
}

// --- 动画主循环 ---
const { pause, resume } = useRafFn(({ delta }) => {
  if (!ctx || !props.enabled) return

  // 1. 清屏
  ctx.clearRect(0, 0, width.value, height.value)
  
  const deltaTime = delta / 16.67 // 归一化系数
  const { speed, opacity, fontSize } = settings.value
  
  // 2. 更新轨道状态（轨道末尾坐标随时间向左移动）
  for (let i = 0; i < trackLastX.value.length; i++) {
    trackLastX.value[i] -= speed * deltaTime
  }

  // 3. 处理现有弹幕
  ctx.globalAlpha = opacity
  for (let i = activeDanmaku.value.length - 1; i >= 0; i--) {
    const d = activeDanmaku.value[i]
    
    // 如果未被鼠标悬停，则更新位置
    if (!d.isHovered) {
      d.x -= speed * deltaTime
    }

    // 移除越界弹幕
    if (d.x + d.textWidth < 0) {
      removeGhostDiv(d.msg.messageId)
      activeDanmaku.value.splice(i, 1)
      continue
    }

    // 更新交互层位置 & 绘制
    updatePosition(d.msg.messageId, d.x, d.y)
    drawDanmaku(d)
  }
  ctx.globalAlpha = 1

  // 4. 尝试从队列注入新弹幕
  const newMsgs = drainQueue()
  for (const msg of newMsgs) {
    if (msg.userId && isBlocked(msg.userId)) continue
    // 密度控制：最多同时存在 60 条
    if (activeDanmaku.value.length > 60) break

    const trackIndex = findAvailableTrack()
    if (trackIndex === -1) continue // 轨道已满，跳过

    const textWidth = ctx.measureText(msg.comment).width
    const mId = msg.messageId || `local_${Math.random().toString(36).slice(2)}`
    
    // 计算轨道 Y 坐标
    const y = trackIndex * (fontSize + 12) + 10

    const danmakuObj: ActiveDanmaku = {
      msg,
      x: width.value,
      y,
      opacity: 1,
      textWidth,
      isHovered: false
    }

    activeDanmaku.value.push(danmakuObj)
    
    // 更新轨道管理器：新弹幕右边缘坐标 = 初始X(width) + 文本宽度
    trackLastX.value[trackIndex] = width.value + textWidth
    
    addGhostDiv(mId, msg.comment, width.value, y, textWidth, fontSize, msg.userId, msg.user_display_name)
  }
})

// --- 事件监听 (VueUse) ---
useEventListener(hitLayerRef, 'mouseover', (e) => {
  const target = e.target as HTMLElement
  if (target.classList.contains('danmaku-ghost')) {
    stopHideTimer()
    const msgId = target.dataset.messageId
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
        messageId: msgId!
      }
    }
  }
})

useEventListener(hitLayerRef, 'mouseout', (e) => {
  if ((e.target as HTMLElement).classList.contains('danmaku-ghost')) {
    startHideTimer()
  }
})

// --- 功能方法 ---
function handleBlockUser() {
  if (!hoveredDanmaku.value.userId) return
  blockUser(hoveredDanmaku.value.userId)
  activeDanmaku.value = activeDanmaku.value.filter(d => {
    if (d.msg.userId === hoveredDanmaku.value.userId) {
      removeGhostDiv(d.msg.messageId); return false
    }
    return true
  })
  hoveredDanmaku.value.show = false
}

function handleHighlightUser() {
  if (hoveredDanmaku.value.userId) highlightUser(hoveredDanmaku.value.userId)
  hoveredDanmaku.value.show = false
}

function clearAll() {
  activeDanmaku.value = []
  trackLastX.value = new Array(trackCount.value).fill(0)
  clearHitLayer()
}

// --- 声明周期 & 监听 ---
watch(() => props.settings, (s) => {
  if (s) {
    Object.assign(settings.value, s)
    applyCanvasFont()
  }
}, { deep: true })

watch(() => props.enabled, (val) => {
  if (val) resume(); else { pause(); clearAll(); }
})

watch(() => props.videoId, () => clearAll())

onUnmounted(() => {
  disconnect()
  clearAll()
})
</script>

<template>
  <div v-if="enabled" ref="containerRef" class="absolute inset-0 overflow-hidden pointer-events-none z-20">
    <canvas
      ref="canvasRef"
      class="absolute inset-0 w-full h-full pointer-events-none"
    />
    
    <div ref="hitLayerRef" class="absolute inset-0 pointer-events-none" />
    
    <!-- 操作菜单 -->
    <div
      v-if="hoveredDanmaku.show"
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