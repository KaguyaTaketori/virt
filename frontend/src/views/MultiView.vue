<template>
  <div class="min-h-screen bg-black text-white">
    <div class="flex items-center justify-between px-4 py-2 bg-[#1a1a1a] border-b border-gray-800 sticky top-0 z-40">
      <div class="flex items-center gap-3">
        <button 
          @click="$router.back()" 
          class="p-2 hover:bg-gray-800 rounded-lg transition text-gray-400 hover:text-white"
          title="返回"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div>
          <h1 class="text-base font-semibold text-white">Multiview</h1>
        </div>
      </div>
      
      <div class="flex items-center gap-2">
        <div class="flex bg-gray-800 rounded-lg p-0.5">
          <button
            v-for="layout in layouts"
            :key="layout.name"
            @click="selectedLayout = layout.name"
            class="px-2 py-1 text-xs rounded-md transition min-w-[32px]"
            :class="selectedLayout === layout.name ? 'bg-pink-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-700'"
          >
            {{ layout.label }}
          </button>
        </div>
        
        <label class="flex items-center gap-1.5 cursor-pointer px-2 py-1.5 hover:bg-gray-800 rounded-lg transition">
          <input type="checkbox" v-model="showDanmaku" class="w-3.5 h-3.5 accent-pink-500 rounded">
          <span class="text-xs text-gray-300">弹幕</span>
        </label>
        
        <button 
          @click="shareUrl" 
          class="p-2 hover:bg-gray-800 rounded-lg transition text-gray-400 hover:text-white"
          title="复制分享链接"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
          </svg>
        </button>
        
        <button 
          @click="showDanmakuSettings = true;" 
          class="p-2 hover:bg-gray-800 rounded-lg transition text-gray-400 hover:text-white"
          title="弹幕设置"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>
    </div>

    <div class="px-4 py-2 bg-[#1a1a1a] border-b border-gray-800">
      <div class="flex flex-wrap gap-2 items-center">
        <select v-model="newChannel.platform" class="bg-[#2a2a2a] border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-300">
          <option value="youtube">YouTube</option>
          <option value="bilibili">Bilibili</option>
        </select>
        <input 
          v-model="newChannel.id" 
          type="text" 
          placeholder="Video ID / Room ID"
          class="bg-[#2a2a2a] border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-300 flex-1 min-w-[120px] placeholder-gray-600"
          @keyup.enter="addChannel"
        />
        <button 
          @click="addChannel" 
          class="px-3 py-1.5 bg-pink-600 hover:bg-pink-700 rounded text-xs font-medium transition"
        >
          Add
        </button>
        
        <div class="flex flex-wrap gap-1.5 ml-auto">
          <span 
            v-for="(ch, idx) in channels" 
            :key="idx"
            class="inline-flex items-center gap-1.5 px-2 py-1 bg-[#2a2a2a] rounded text-xs"
          >
            <span class="text-gray-500">{{ ch.platform === 'youtube' ? 'YT' : 'B' }}</span>
            <span class="max-w-[80px] truncate text-gray-300">{{ ch.id }}</span>
            <button 
              @click="removeChannel(idx)" 
              class="text-gray-600 hover:text-red-400 transition"
            >
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </span>
        </div>
      </div>
    </div>

    <div class="p-1 bg-black min-h-0 flex-1">
      <div 
        class="grid gap-0.5 h-full"
        :style="gridStyle"
      >
        <div 
          v-for="(ch, idx) in channels" 
          :key="idx"
          class="relative bg-[#0a0a0a] overflow-hidden group"
          style="aspect-ratio: 16/9;"
        >
          <iframe
            v-if="getEmbedUrl(ch)"
            :src="getEmbedUrl(ch)"
            class="absolute inset-0 w-full h-full"
            frameborder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen
          ></iframe>

          <!-- Canvas：永远 pointer-events: none，只负责绘制 -->
          <canvas
            v-if="showDanmaku && ch.platform === 'youtube'"
            :ref="el => { if (el) danmakuCanvases[idx] = el }"
            class="absolute inset-0 w-full h-full"
            style="pointer-events: none;"
          ></canvas>

          <!--
            Hit-layer：容器本身 pointer-events: none，
            由 JS 动态插入的子 div 承载 pointer-events: auto。
            这样只有弹幕文字包围盒内才会拦截事件，
            其余区域的所有鼠标操作（进度条拖拽等）直接穿透到 iframe。
            Bilibili 使用播放器自带弹幕，不需要此层。
          -->
          <div
            v-if="showDanmaku && ch.platform === 'youtube'"
            :ref="el => { if (el) danmakuHitLayers[idx] = el }"
            class="absolute inset-0"
            style="pointer-events: none;"
          ></div>

          <div class="absolute top-1 left-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <span class="px-1.5 py-0.5 bg-black/70 rounded text-[10px] text-gray-300">
              {{ ch.platform === 'youtube' ? 'YouTube' : 'Bilibili' }}
            </span>
          </div>
          <div class="absolute bottom-0 left-0 right-0 p-1.5 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
            <div class="flex items-center justify-between">
              <span class="text-xs truncate max-w-[150px]">{{ ch.id }}</span>
              <button 
                @click.stop="removeChannel(idx)" 
                class="p-1 bg-red-600/80 hover:bg-red-600 rounded transition"
              >
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <div 
          v-for="n in emptyCellCount" 
          :key="'empty-' + n"
          class="relative bg-[#0a0a0a] border-2 border-dashed border-gray-800 hover:border-gray-700 transition-colors cursor-pointer"
          style="aspect-ratio: 16/9;"
          @click="focusInput"
        >
          <div class="absolute inset-0 flex flex-col items-center justify-center text-gray-600 hover:text-gray-400 transition-colors">
            <svg class="w-8 h-8 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 4v16m8-8H4" />
            </svg>
            <span class="text-xs">Add Video</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="channels.length === 0" class="flex flex-col items-center justify-center h-[50vh] text-gray-500 bg-black">
      <svg class="w-14 h-14 mb-3 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
      </svg>
      <p class="text-base mb-1">Add videos to start multiview</p>
      <p class="text-xs text-gray-600">Enter YouTube video ID or Bilibili room ID above</p>
    </div>

    <!-- 弹幕右键菜单：mouseenter 取消隐藏计时器，mouseleave 触发隐藏 -->
    <div
      v-if="hoveredDanmaku.show"
      class="fixed bg-gray-800 rounded-lg shadow-xl z-50 py-2 min-w-[160px]"
      :style="getHoveredMenuStyle()"
      @mouseenter="cancelHideMenu"
      @mouseleave="startHideMenu"
    >
      <div class="px-3 py-1 text-xs text-gray-400 border-b border-gray-700 mb-1">
        {{ hoveredDanmaku.displayName || hoveredDanmaku.userId }}
      </div>
      <button @click="addRuleFromHover('highlight')" class="w-full px-4 py-2 text-left text-sm hover:bg-gray-700">高亮</button>
      <button @click="addRuleFromHover('block')" class="w-full px-4 py-2 text-left text-sm hover:bg-gray-700 text-red-400">屏蔽</button>
    </div>

    <div v-if="showDanmakuSettings" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="showDanmakuSettings = false">
      <div class="bg-gray-800 rounded-lg p-6 w-[500px] max-h-[80vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-xl font-bold">弹幕设置</h2>
          <button @click="showDanmakuSettings = false" class="text-gray-400 hover:text-white">×</button>
        </div>

        <div class="mb-6">
          <h3 class="text-sm font-semibold text-gray-300 mb-3">全局样式</h3>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs text-gray-400 mb-1">字体大小</label>
              <input type="number" v-model.number="danmakuSettings.global.fontSize" min="12" max="36" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-1">
            </div>
            <div>
              <label class="block text-xs text-gray-400 mb-1">弹幕速度</label>
              <input type="number" v-model.number="danmakuSettings.global.speed" min="1" max="6" step="0.5" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-1">
            </div>
            <div>
              <label class="block text-xs text-gray-400 mb-1">不透明度</label>
              <input type="range" v-model.number="danmakuSettings.global.opacity" min="0.3" max="1" step="0.1" class="w-full">
              <span class="text-xs text-gray-400">{{ danmakuSettings.global.opacity }}</span>
            </div>
            <div>
              <label class="block text-xs text-gray-400 mb-1">默认颜色</label>
              <div class="flex gap-2 flex-wrap">
                <button 
                  v-for="c in defaultColors" 
                  :key="c"
                  @click="danmakuSettings.global.color = c"
                  :style="{ backgroundColor: c }"
                  class="w-6 h-6 rounded border-2"
                  :class="danmakuSettings.global.color === c ? 'border-white' : 'border-transparent'"
                ></button>
              </div>
            </div>
          </div>
          
          <div class="mt-4 pt-4 border-t border-gray-700">
            <div class="flex items-center gap-4 mb-3">
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" v-model="danmakuSettings.global.strokeEnabled" class="w-4 h-4 accent-pink-500">
                <span class="text-sm text-gray-300">描边</span>
              </label>
              <template v-if="danmakuSettings.global.strokeEnabled">
                <input 
                  v-model="danmakuSettings.global.strokeColor"
                  type="color"
                  class="w-8 h-8 rounded cursor-pointer"
                >
                <div class="flex items-center gap-2">
                  <span class="text-xs text-gray-400">宽度</span>
                  <input 
                    type="number" 
                    v-model.number="danmakuSettings.global.strokeWidth" 
                    min="0" 
                    max="8" 
                    class="w-16 bg-gray-700 border border-gray-600 rounded px-2 py-1"
                  >
                </div>
              </template>
            </div>
          </div>
        </div>

        <div class="mb-6">
          <h3 class="text-sm font-semibold text-gray-300 mb-3">用户管理 (仅YouTube)</h3>
          <div class="flex gap-2 mb-3">
            <input 
              v-model="newUserRule.userId" 
              type="text" 
              placeholder="用户ID或名称"
              class="bg-gray-700 border border-gray-600 rounded px-3 py-1 flex-1"
            >
            <select v-model="newUserRule.action" class="bg-gray-700 border border-gray-600 rounded px-3 py-1">
              <option value="block">屏蔽</option>
              <option value="highlight">高亮</option>
            </select>
            <input 
              v-if="newUserRule.action === 'highlight'"
              v-model="newUserRule.color"
              type="color"
              class="w-10 h-8 rounded cursor-pointer"
            >
            <button @click="addUserRule" class="px-3 py-1 bg-pink-600 rounded hover:bg-pink-700">添加</button>
          </div>
          
          <div class="space-y-2 max-h-48 overflow-y-auto">
            <div 
              v-for="(rule, userId) in danmakuSettings.userRules" 
              :key="userId"
              class="flex items-center gap-2 bg-gray-700 rounded px-3 py-2"
            >
              <span class="flex-1 text-sm truncate" :title="userId">{{ userId }}</span>
              <span 
                class="px-2 py-0.5 rounded text-xs"
                :class="rule.action === 'block' ? 'bg-red-900 text-red-200' : 'bg-yellow-900 text-yellow-200'"
              >
                {{ rule.action === 'block' ? '屏蔽' : '高亮' }}
              </span>
              <span v-if="rule.action === 'highlight'" class="w-4 h-4 rounded" :style="{ backgroundColor: rule.color }"></span>
              <button @click="removeUserRule(userId)" class="text-gray-400 hover:text-red-400">×</button>
            </div>
            <p v-if="Object.keys(danmakuSettings.userRules).length === 0" class="text-gray-500 text-sm text-center py-2">
              暂无用户规则
            </p>
          </div>
        </div>

        <div class="flex justify-between gap-2">
          <button @click="resetDanmakuSettings" class="px-4 py-2 bg-gray-700 rounded hover:bg-gray-600 text-sm">恢复默认</button>
          <button @click="showDanmakuSettings = false" class="px-4 py-2 bg-gray-700 rounded hover:bg-gray-600">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const newChannel = ref({ platform: 'youtube', id: '' })
const channels = ref([])
const showDanmaku = ref(false)
const showDanmakuSettings = ref(false)

// Canvas refs（只负责绘制，pointer-events 始终为 none）
const danmakuCanvases = ref([])

// Hit-layer refs（容器 pointer-events: none，子 div 动态插入并设为 auto）
// 只对 YouTube 频道创建，Bilibili 使用播放器自带弹幕
const danmakuHitLayers = ref([])

// 每个频道的 Map<messageId, HTMLDivElement>，用于复用 div 避免每帧重建 DOM
// 使用普通数组而非 ref，不需要响应式追踪
const hitLayerDivMaps: Map<string, HTMLDivElement>[] = []

const danmakuContexts = ref([])
const danmakuTimers = ref([])
const danmakuQueues = ref([])

const wsConnections = ref({})
const reconnectTimers = ref({})
const stickerImages = ref({})

// 菜单显示/隐藏的延迟计时器
// 给用户 150ms 的时间从弹幕 div 移动到菜单，防止途中触发 mouseleave 导致菜单消失
let hideMenuTimer: ReturnType<typeof setTimeout> | null = null

const defaultColors = ['#ffffff', '#ff6b6b', '#ffd700', '#90EE90', '#87CEEB', '#ff69b4']

const defaultDanmakuSettings = {
  global: {
    fontSize: 20,
    speed: 2,
    opacity: 1,
    color: '#ffffff',
    strokeEnabled: true,
    strokeColor: '#000000',
    strokeWidth: 2
  },
  userRules: {}
}

const danmakuSettings = ref({ ...defaultDanmakuSettings })
const newUserRule = ref({ userId: '', action: 'block', color: '#ff6b6b' })

// 悬停状态：改用 menuRect 存储触发位置，由 getBoundingClientRect() 提供精确坐标
// 不再依赖 Canvas 坐标换算
const hoveredDanmaku = ref({
  show: false,
  userId: '',
  displayName: '',
  idx: -1,
  menuRect: null as DOMRect | null,
})

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const WS_BASE = import.meta.env.VITE_WS_BASE || 'ws://localhost:8000'

const layouts = [
  { name: '1x1', label: '1×1', cols: 1, cells: 1 },
  { name: '2x1', label: '2×1', cols: 2, cells: 2 },
  { name: '2x2', label: '2×2', cols: 2, cells: 4 },
  { name: '3x2', label: '3×2', cols: 3, cells: 6 },
  { name: '3x3', label: '3×3', cols: 3, cells: 9 },
  { name: '4x3', label: '4×3', cols: 4, cells: 12 },
  { name: '4x4', label: '4×4', cols: 4, cells: 16 },
]

const selectedLayout = ref('2x2')

const gridStyle = computed(() => {
  const layout = layouts.find(l => l.name === selectedLayout.value) || layouts[2]
  return {
    gridTemplateColumns: `repeat(${layout.cols}, 1fr)`,
    minHeight: 'calc(100vh - 120px)'
  }
})

const emptyCellCount = computed(() => {
  const layout = layouts.find(l => l.name === selectedLayout.value) || layouts[2]
  return Math.max(0, layout.cells - channels.value.length)
})

// ─── 菜单控制 ────────────────────────────────────────────────────────────────

/**
 * 取消挂起的隐藏计时器。
 * 在弹幕 hit-div 或菜单本身的 mouseenter 中调用。
 */
function cancelHideMenu() {
  if (hideMenuTimer !== null) {
    clearTimeout(hideMenuTimer)
    hideMenuTimer = null
  }
}

/**
 * 启动延迟隐藏。
 * 在弹幕 hit-div 或菜单本身的 mouseleave 中调用。
 * 150ms 的缓冲足够用户从弹幕文字移动到菜单，同时短到不影响使用体验。
 */
function startHideMenu() {
  cancelHideMenu()
  hideMenuTimer = setTimeout(() => {
    hoveredDanmaku.value.show = false
    hideMenuTimer = null
  }, 150)
}

/**
 * 根据 menuRect 计算菜单位置。
 * 使用 getBoundingClientRect 提供的视口坐标，避免 Canvas 坐标换算误差。
 */
function getHoveredMenuStyle() {
  const rect = hoveredDanmaku.value.menuRect
  if (!rect) return { bottom: '20px', right: '20px' }

  const MENU_HEIGHT = 140
  const MENU_WIDTH = 160
  const GAP = 6

  // 优先在弹幕下方展开，空间不足时改为上方
  const spaceBelow = window.innerHeight - rect.bottom
  const top = spaceBelow >= MENU_HEIGHT + GAP
    ? rect.bottom + GAP
    : rect.top - MENU_HEIGHT - GAP

  // 右侧超出视口时左移
  let left = rect.left
  if (left + MENU_WIDTH > window.innerWidth - 10) {
    left = window.innerWidth - MENU_WIDTH - 10
  }

  return {
    top: `${Math.max(10, top)}px`,
    left: `${Math.max(10, left)}px`,
  }
}

// ─── Hit-layer 管理 ───────────────────────────────────────────────────────────

/**
 * 每帧渲染后同步 hit-layer 中的子 div 位置。
 *
 * 策略：
 * - 以 messageId 为 key 复用 div，避免每帧重建 DOM 节点
 * - 用 transform: translate 更新位置（不触发 layout reflow）
 * - 移出屏幕的弹幕从 Map 中删除，对应 div 从 DOM 移除
 * - sticker 类型不参与 hit 检测（无用户信息）
 */
function updateHitLayer(idx: number, queue: any[]) {
  const hitLayer = danmakuHitLayers.value[idx]
  if (!hitLayer) return

  if (!hitLayerDivMaps[idx]) {
    hitLayerDivMaps[idx] = new Map()
  }
  const map = hitLayerDivMaps[idx]
  const { fontSize } = danmakuSettings.value.global

  // 收集当前帧仍存活的 messageId
  const currentIds = new Set<string>()

  for (const msg of queue) {
    // sticker 不做 hit 检测；无 messageId 的消息无法稳定追踪
    if (msg.messageType === 'sticker' || !msg.messageId) continue

    currentIds.add(msg.messageId)

    let div = map.get(msg.messageId)

    if (!div) {
      // 首次出现：创建 div 并绑定事件
      div = document.createElement('div')
      div.style.cssText = [
        'position: absolute',
        'top: 0',
        'left: 0',
        // 关键：只有这些子 div 有 pointer-events，容器本身为 none
        'pointer-events: auto',
        'cursor: pointer',
        // 透明背景，不遮挡视频画面
        'background: transparent',
      ].join(';')

      // 捕获当前 msg 的闭包值（div 创建时已绑定）
      const capturedMsg = msg

      div.addEventListener('mouseenter', () => {
        cancelHideMenu()
        // 使用 getBoundingClientRect 获取视口精确坐标，无需 Canvas 换算
        hoveredDanmaku.value = {
          show: true,
          userId: capturedMsg.userId || '',
          displayName: capturedMsg.userDisplayName || '',
          idx,
          menuRect: div!.getBoundingClientRect(),
        }
      })

      div.addEventListener('mouseleave', startHideMenu)

      map.set(msg.messageId, div)
      hitLayer.appendChild(div)
    }

    // 每帧只更新 transform 和尺寸，不触发 layout
    div.style.transform = `translate(${msg.x}px, ${msg.y}px)`
    div.style.width = `${msg.textWidth || 60}px`
    div.style.height = `${fontSize + 4}px`
  }

  // 清理已离屏（被 renderDanmaku 从队列移除）的 div
  for (const [id, div] of map) {
    if (!currentIds.has(id)) {
      div.remove()
      map.delete(id)
    }
  }
}

/**
 * 清空指定频道的 hit-layer，释放 DOM 节点。
 */
function clearHitLayer(idx: number) {
  const map = hitLayerDivMaps[idx]
  if (!map) return
  for (const div of map.values()) {
    div.remove()
  }
  map.clear()
}

// ─── 其余原有逻辑（保持不变）────────────────────────────────────────────────

function focusInput() {
  const input = document.querySelector('input[placeholder="Video ID / Room ID"]') as HTMLInputElement
  if (input) input.focus()
}

function getEmbedUrl(ch) {
  if (ch.platform === 'youtube') {
    return `https://www.youtube.com/embed/${ch.id}`
  } else if (ch.platform === 'bilibili') {
    return `https://www.bilibili.com/blackboard/live/live-activity-player.html?cid=${ch.id}&quality=0`
  }
  return null
}

function parseYouTubeId(input) {
  if (!input) return null
  try {
    const url = new URL(input)
    if (url.hostname.includes('youtube.com')) return url.searchParams.get('v')
    if (url.hostname.includes('youtu.be')) return url.pathname.slice(1)
  } catch {
    return input
  }
  return input
}

function addChannel() {
  if (!newChannel.value.id) return
  const id = newChannel.value.platform === 'youtube'
    ? parseYouTubeId(newChannel.value.id)
    : newChannel.value.id
  if (!id) return
  channels.value.push({ platform: newChannel.value.platform, id })
  newChannel.value.id = ''
  localStorage.setItem('multiview_channels', JSON.stringify(channels.value))
  if (showDanmaku.value) initDanmaku()
}

function removeChannel(idx) {
  const ch = channels.value[idx]
  if (ch && ch.platform === 'youtube') disconnectWs(ch.id)

  // 清理对应频道的 hit-layer
  clearHitLayer(idx)
  hitLayerDivMaps.splice(idx, 1)
  danmakuHitLayers.value.splice(idx, 1)

  channels.value.splice(idx, 1)
  localStorage.setItem('multiview_channels', JSON.stringify(channels.value))
}

function loadDanmakuSettings() {
  const saved = localStorage.getItem('multiview_danmaku_settings')
  if (saved) {
    try { danmakuSettings.value = { ...defaultDanmakuSettings, ...JSON.parse(saved) } }
    catch (e) { console.error('Failed to load danmaku settings:', e) }
  }
}

function saveDanmakuSettings() {
  localStorage.setItem('multiview_danmaku_settings', JSON.stringify(danmakuSettings.value))
}

function resetDanmakuSettings() {
  danmakuSettings.value = JSON.parse(JSON.stringify(defaultDanmakuSettings))
  saveDanmakuSettings()
}

function addUserRule() {
  if (!newUserRule.value.userId) return
  const userId = newUserRule.value.userId.trim()
  if (danmakuSettings.value.userRules[userId]) { alert('该用户规则已存在'); return }
  danmakuSettings.value.userRules[userId] = {
    action: newUserRule.value.action,
    color: newUserRule.value.action === 'highlight' ? newUserRule.value.color : null
  }
  newUserRule.value.userId = ''
  saveDanmakuSettings()
}

function removeUserRule(userId) {
  delete danmakuSettings.value.userRules[userId]
  saveDanmakuSettings()
}

function getUserRule(userId, displayName) {
  if (danmakuSettings.value.userRules[userId]) return danmakuSettings.value.userRules[userId]
  if (displayName && danmakuSettings.value.userRules[displayName]) return danmakuSettings.value.userRules[displayName]
  return null
}

function addRuleFromHover(action) {
  const { userId, displayName } = hoveredDanmaku.value
  const targetId = userId || displayName
  if (!targetId) return
  if (danmakuSettings.value.userRules[targetId]) {
    alert('该用户规则已存在')
  } else {
    danmakuSettings.value.userRules[targetId] = {
      action,
      color: action === 'highlight' ? '#ff6b6b' : null
    }
    saveDanmakuSettings()
  }
  hoveredDanmaku.value.show = false
}

function shareUrl() {
  if (channels.value.length === 0) { alert('请先添加频道'); return }
  const channelStr = channels.value.map(ch => `${ch.platform}_${ch.id}`).join(',')
  const shareCode = btoa(channelStr)
  const url = `${window.location.origin}/multiview?c=${shareCode}`
  navigator.clipboard.writeText(url)
    .then(() => alert('分享链接已复制到剪贴板'))
    .catch(() => prompt('分享链接：', url))
}

// ─── WebSocket ────────────────────────────────────────────────────────────────

function connectWs(videoId) {
  if (wsConnections.value[videoId]) return
  const ws = new WebSocket(`${WS_BASE}/ws/danmaku/${videoId}`)
  ws.onopen = () => { delete reconnectTimers.value[videoId] }
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'danmaku' && data.data) addDanmakuMessages(videoId, data.data)
    } catch (e) { console.error('Failed to parse danmaku message:', e) }
  }
  ws.onclose = () => {
    delete wsConnections.value[videoId]
    if (showDanmaku.value) scheduleReconnect(videoId)
  }
  ws.onerror = (error) => { console.error(`WebSocket error for ${videoId}:`, error) }
  wsConnections.value[videoId] = ws
}

function disconnectWs(videoId) {
  const ws = wsConnections.value[videoId]
  if (ws) { ws.close(); delete wsConnections.value[videoId] }
  if (reconnectTimers.value[videoId]) {
    clearTimeout(reconnectTimers.value[videoId])
    delete reconnectTimers.value[videoId]
  }
}

function scheduleReconnect(videoId) {
  if (reconnectTimers.value[videoId]) return
  reconnectTimers.value[videoId] = setTimeout(() => {
    delete reconnectTimers.value[videoId]
    if (showDanmaku.value) connectWs(videoId)
  }, 3000)
}

// ─── 弹幕队列 ────────────────────────────────────────────────────────────────

/**
 * 将 WebSocket 推送的消息加入对应频道的渲染队列。
 * 现在同时存储 userId / userDisplayName / messageId 用于 hit-layer 交互。
 */
function addDanmakuMessages(videoId, messages) {
  const idx = channels.value.findIndex(ch => ch.id === videoId)
  if (idx === -1) return

  const queue = danmakuQueues.value[idx] || []
  const rule = (msg) => getUserRule(msg.user_id || '', msg.user_display_name || '')

  messages.forEach(msg => {
    // sticker
    if (msg.message_type === 'sticker' && msg.sticker_url) {
      queue.push({
        messageType: 'sticker',
        sticker_url: msg.sticker_url,
        alt_text: msg.alt_text || 'Sticker',
        messageId: msg.message_id || '',
        x: 800,
        y: 50 + Math.random() * 300,
        textWidth: 50,
        loaded: false,
      })
      if (!stickerImages.value[msg.sticker_url]) {
        const img = new Image()
        img.onload = () => {
          stickerImages.value[msg.sticker_url] = img
          queue.forEach(m => { if (m.sticker_url === msg.sticker_url) m.loaded = true })
        }
        img.onerror = () => { stickerImages.value[msg.sticker_url] = null }
        img.src = msg.sticker_url
      }
      return
    }

    const content = msg.comment || msg.message || ''
    if (!content) return

    const userRule = rule(msg)
    // 屏蔽规则：直接跳过，不加入队列
    if (userRule?.action === 'block') return

    const colors = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff', '#ffffff', '#ffaa00', '#aaff00', '#00aaff']
    // 高亮规则：使用指定颜色，否则随机
    const color = userRule?.action === 'highlight' && userRule.color
      ? userRule.color
      : colors[Math.floor(Math.random() * colors.length)]

    queue.push({
      messageType: 'text',
      content,
      color,
      // 用于 hit-layer 悬停菜单
      userId: msg.user_id || '',
      userDisplayName: msg.user_display_name || '',
      messageId: msg.message_id || `dm_${Date.now()}_${Math.random()}`,
      x: 800,
      y: 50 + Math.random() * 300,
      textWidth: 0, // 在 renderDanmaku 中首次绘制时计算并缓存
    })
  })

  danmakuQueues.value[idx] = queue
}

// ─── Canvas 渲染 ──────────────────────────────────────────────────────────────

onMounted(() => {
  loadDanmakuSettings()

  const shareCode = Array.isArray(route.query.c) ? route.query.c[0] : route.query.c
  if (shareCode) {
    try {
      const decoded = atob(shareCode)
      const channelList = decoded.split(',').map(item => {
        const [platform, id] = item.split('_')
        return { platform, id }
      }).filter(ch => ch.platform && ch.id)
      if (channelList.length > 0) {
        channels.value = channelList
        localStorage.setItem('multiview_channels', JSON.stringify(channelList))
        router.replace({ name: 'MultiView' })
        return
      }
    } catch (e) { console.error('Failed to parse share code:', e) }
  }

  const saved = localStorage.getItem('multiview_channels')
  if (saved) {
    try { channels.value = JSON.parse(saved) }
    catch (e) { console.error('Failed to restore channels:', e) }
  }
})

watch(showDanmaku, async (enabled) => {
  if (enabled) {
    await nextTick()
    initDanmaku()
  } else {
    stopDanmaku()
  }
})

function initDanmaku() {
  channels.value.forEach((ch, idx) => {
    // 只对 YouTube 频道初始化 Canvas 弹幕
    if (ch.platform !== 'youtube') return

    const canvas = danmakuCanvases.value[idx]
    if (!canvas) return

    const rect = canvas.parentElement.getBoundingClientRect()
    canvas.width = rect.width
    canvas.height = rect.height

    const ctx = canvas.getContext('2d')
    danmakuContexts.value[idx] = { ctx, canvas }
    danmakuQueues.value[idx] = []

    // 初始化对应频道的 hit-layer Map
    if (!hitLayerDivMaps[idx]) hitLayerDivMaps[idx] = new Map()

    connectWs(ch.id)
    startDanmakuLoop(idx)
  })

  window.addEventListener('resize', handleResize)
}

function handleResize() {
  if (!showDanmaku.value) return
  channels.value.forEach((ch, idx) => {
    if (ch.platform !== 'youtube') return
    const canvas = danmakuCanvases.value[idx]
    if (!canvas) return
    const rect = canvas.parentElement.getBoundingClientRect()
    canvas.width = rect.width
    canvas.height = rect.height
    const ctx = canvas.getContext('2d')
    danmakuContexts.value[idx] = { ...danmakuContexts.value[idx], ctx, canvas }
  })
}

function stopDanmaku() {
  danmakuTimers.value.forEach(t => clearInterval(t))
  danmakuTimers.value = []
  danmakuContexts.value = []
  danmakuQueues.value = []

  // 清理所有 hit-layer DOM 节点
  hitLayerDivMaps.forEach((map, idx) => {
    if (map) {
      for (const div of map.values()) div.remove()
      map.clear()
    }
  })
  hitLayerDivMaps.length = 0
  danmakuHitLayers.value = []

  // 取消挂起的菜单隐藏计时器并收起菜单
  cancelHideMenu()
  hoveredDanmaku.value.show = false

  Object.keys(wsConnections.value).forEach(videoId => disconnectWs(videoId))
}

function startDanmakuLoop(idx) {
  const timer = setInterval(() => renderDanmaku(idx), 30)
  danmakuTimers.value.push(timer)
}

/**
 * 主渲染函数，每帧：
 * 1. 清空 Canvas
 * 2. 绘制所有弹幕，计算并缓存 textWidth
 * 3. 调用 updateHitLayer 同步 hit-layer 子 div 的位置
 */
function renderDanmaku(idx) {
  const ctxData = danmakuContexts.value[idx]
  if (!ctxData) return
  const { ctx } = ctxData
  const queue = danmakuQueues.value[idx]
  if (!ctx || !queue || queue.length === 0) return

  const canvas = danmakuCanvases.value[idx]
  if (!canvas) return

  const { fontSize, speed, opacity, strokeEnabled, strokeColor, strokeWidth } =
    danmakuSettings.value.global

  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.font = `${fontSize}px sans-serif`
  ctx.textBaseline = 'top'
  ctx.globalAlpha = opacity

  for (let i = queue.length - 1; i >= 0; i--) {
    const msg = queue[i]
    msg.x -= speed

    if (msg.messageType === 'sticker') {
      if (msg.x < -70) { queue.splice(i, 1); continue }
      const img = stickerImages.value[msg.sticker_url]
      if (img) ctx.drawImage(img, msg.x, msg.y, 50, 50)
      continue
    }

    // 计算文字宽度并缓存到 msg.textWidth，供 updateHitLayer 使用
    const textWidth = ctx.measureText(msg.content || '').width
    msg.textWidth = textWidth

    if (msg.x < -(textWidth + 20)) {
      queue.splice(i, 1)
      continue
    }

    if (strokeEnabled) {
      ctx.strokeStyle = strokeColor
      ctx.lineWidth = strokeWidth
      ctx.strokeText(msg.content || '', msg.x, msg.y)
    }

    ctx.fillStyle = msg.color || danmakuSettings.value.global.color
    ctx.fillText(msg.content || '', msg.x, msg.y)
  }

  ctx.globalAlpha = 1

  // 同步 hit-layer：根据当前帧队列状态更新 div 位置
  updateHitLayer(idx, queue)
}

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  stopDanmaku()
})
</script>