<template>
  <div class="container mx-auto px-4 py-8">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold">多窗播放</h1>
        <p class="text-gray-400 text-sm mt-1">同时观看多个直播</p>
      </div>
      <div class="flex items-center gap-4">
        <label class="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" v-model="showDanmaku" class="w-4 h-4 accent-pink-500">
          <span class="text-sm text-gray-300">弹幕</span>
        </label>
        <button 
          @click="shareUrl" 
          class="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700 transition"
          title="复制分享链接"
        >
          分享
        </button>
        <button 
          @click="showDanmakuSettings = true" 
          class="px-3 py-1 bg-gray-700 rounded hover:bg-gray-600 transition text-sm"
          title="弹幕设置"
        >
          设置
        </button>
        <button 
          @click="$router.back()" 
          class="px-4 py-2 bg-gray-700 rounded hover:bg-gray-600 transition"
        >
          返回
        </button>
      </div>
    </div>

    <div class="bg-gray-800 rounded-lg p-4 mb-6">
      <div class="flex flex-wrap gap-4 items-center">
        <div class="flex-1 min-w-[200px]">
          <label class="block text-sm text-gray-400 mb-2">添加频道</label>
          <div class="flex gap-2">
            <select v-model="newChannel.platform" class="bg-gray-700 border border-gray-600 rounded px-3 py-2">
              <option value="youtube">YouTube</option>
              <option value="bilibili">Bilibili</option>
            </select>
            <input 
              v-model="newChannel.id" 
              type="text" 
              placeholder="视频ID/房间ID"
              class="bg-gray-700 border border-gray-600 rounded px-3 py-2 flex-1"
            />
            <button 
              @click="addChannel" 
              class="px-4 py-2 bg-pink-600 rounded hover:bg-pink-700 transition"
            >
              添加
            </button>
          </div>
        </div>
      </div>

      <div class="mt-4 flex flex-wrap gap-2">
        <span 
          v-for="(ch, idx) in channels" 
          :key="idx"
          class="inline-flex items-center gap-2 px-3 py-1 bg-gray-700 rounded-full"
        >
          <span class="text-sm">{{ ch.platform }}: {{ ch.id }}</span>
          <button 
            @click="removeChannel(idx)" 
            class="text-gray-400 hover:text-red-400"
          >
            ×
          </button>
        </span>
      </div>
    </div>

    <div 
      class="grid gap-4"
      :style="gridStyle"
    >
      <div 
        v-for="(ch, idx) in channels" 
        :key="idx"
        class="relative bg-black rounded-lg overflow-hidden"
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
        <canvas
          v-if="showDanmaku"
          :ref="el => danmakuCanvases[idx] = el"
          class="absolute inset-0 w-full h-full pointer-events-none"
        ></canvas>
        <div
          v-if="showDanmaku && ch.platform === 'youtube'"
          :ref="el => { if (el) hitboxLayers[idx] = el }"
          class="absolute inset-0 pointer-events-none"
        ></div>
        <div v-if="!getEmbedUrl(ch)" class="flex items-center justify-center h-full text-gray-500">
          无效的嵌入链接
        </div>
      </div>
    </div>

    <div v-if="channels.length === 0" class="text-center py-12 text-gray-500">
      <p class="text-xl">添加频道开始多窗观看</p>
    </div>

    <div v-if="hoveredDanmaku.show" class="fixed bg-gray-800 rounded-lg shadow-xl z-50 py-2 min-w-[160px]" :style="getHoveredMenuStyle()">
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

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const newChannel = ref({
  platform: 'youtube',
  id: ''
})

const channels = ref([])
const showDanmaku = ref(false)
const showDanmakuSettings = ref(false)
const danmakuCanvases = ref([])
const danmakuContexts = ref([])
const danmakuTimers = ref([])
const danmakuQueues = ref([])
const trackStates = ref([])

const TRACK_TOP_OFFSET = 10

const wsConnections = ref({})
const reconnectTimers = ref({})
const stickerImages = ref({})

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
const hitboxLayers = ref([])
const hitboxPool = ref([])
const MAX_HITBOXES = 50

const hoveredDanmaku = ref({ 
  show: false, 
  userId: '', 
  displayName: '', 
  idx: -1,
  danmakuX: 0,
  danmakuY: 0,
  danmakuWidth: 100,
  danmakuHeight: 28
})

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const WS_BASE = import.meta.env.VITE_WS_BASE || 'ws://localhost:8000'

const gridStyle = computed(() => {
  const count = channels.value.length
  if (count <= 1) return { gridTemplateColumns: '1fr' }
  if (count <= 2) return { gridTemplateColumns: 'repeat(2, 1fr)' }
  if (count <= 4) return { gridTemplateColumns: 'repeat(2, 1fr)' }
  return { gridTemplateColumns: 'repeat(3, 1fr)' }
})

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
    if (url.hostname.includes('youtube.com')) {
      return url.searchParams.get('v')
    } else if (url.hostname.includes('youtu.be')) {
      return url.pathname.slice(1)
    }
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
  
  if (showDanmaku.value) {
    initDanmaku()
  }
}

function removeChannel(idx) {
  const ch = channels.value[idx]
  if (ch && ch.platform === 'youtube') {
    disconnectWs(ch.id)
  }
  channels.value.splice(idx, 1)
  localStorage.setItem('multiview_channels', JSON.stringify(channels.value))
}

function loadDanmakuSettings() {
  const saved = localStorage.getItem('multiview_danmaku_settings')
  if (saved) {
    try {
      danmakuSettings.value = { ...defaultDanmakuSettings, ...JSON.parse(saved) }
    } catch (e) {
      console.error('Failed to load danmaku settings:', e)
    }
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
  if (danmakuSettings.value.userRules[userId]) {
    alert('该用户规则已存在')
    return
  }
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

function getFontSize() {
  return danmakuSettings.value.global.fontSize || 20
}

function getTrackHeight() {
  return getFontSize() + 8
}

function initTrackState(idx, canvasHeight) {
  const trackHeight = getTrackHeight()
  const numTracks = Math.floor((canvasHeight - TRACK_TOP_OFFSET) / trackHeight)
  trackStates.value[idx] = Array.from({ length: numTracks }, () => ({ tailX: 0 }))
}

function getUserRule(userId, displayName) {
  if (danmakuSettings.value.userRules[userId]) {
    return danmakuSettings.value.userRules[userId]
  }
  if (displayName && danmakuSettings.value.userRules[displayName]) {
    return danmakuSettings.value.userRules[displayName]
  }
  return null

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
}

function initHitboxPool() {
  for (let i = 0; i < MAX_HITBOXES; i++) {
    const el = document.createElement('div')
    el.className = 'danmaku-hitbox'
    el.style.cssText = 'position: absolute; pointer-events: auto; cursor: pointer; display: none;'
    el.dataset.userId = ''
    el.dataset.displayName = ''
    el.dataset.idx = '-1'
    el.addEventListener('mouseenter', handleHitboxHover)
    el.addEventListener('mouseleave', handleHitboxLeave)
    document.body.appendChild(el)
    hitboxPool.value.push({ el, inUse: false })
  }
}

function getHitboxFromPool() {
  const hitbox = hitboxPool.value.find(h => !h.inUse)
  if (hitbox) {
    hitbox.inUse = true
    hitbox.el.style.display = 'block'
    return hitbox
  }
  return null
}

function returnHitboxToPool(hitbox) {
  hitbox.inUse = false
  hitbox.el.style.display = 'none'
}

function handleHitboxHover(event) {
  const el = event.target
  const userId = el.dataset.userId || ''
  const displayName = el.dataset.displayName || ''
  const idx = parseInt(el.dataset.idx) || -1
  
  if (!userId && !displayName) return

  hoveredDanmaku.value = {
    show: true,
    userId,
    displayName,
    idx,
    danmakuX: parseFloat(el.style.left) || 0,
    danmakuY: parseFloat(el.style.top) || 0,
    danmakuWidth: parseFloat(el.style.width) || 100,
    danmakuHeight: 28
  }
}

function handleHitboxLeave() {
  hoveredDanmaku.value.show = false
}

function updateHitboxPosition(hitbox, x, y, width, height) {
  hitbox.el.style.left = x + 'px'
  hitbox.el.style.top = y + 'px'
  hitbox.el.style.width = width + 'px'
  hitbox.el.style.height = height + 'px'
}

function getHoveredMenuStyle() {
  const idx = hoveredDanmaku.value.idx
  const canvas = danmakuCanvases.value[idx]
  if (!canvas) return { bottom: '20px', right: '20px' }

  const wrapper = canvas.parentElement
  if (!wrapper) return { bottom: '20px', right: '20px' }

  const rect = wrapper.getBoundingClientRect()
  const danmakuY = hoveredDanmaku.value.danmakuY || 0
  const danmakuX = hoveredDanmaku.value.danmakuX || 0
  const danmakuWidth = hoveredDanmaku.value.danmakuWidth || 100
  const danmakuHeight = hoveredDanmaku.value.danmakuHeight || 28

  const menuHeight = 140

  const absoluteY = rect.top + danmakuY
  const absoluteX = rect.left + danmakuX

  const spaceBelow = window.innerHeight - absoluteY - danmakuHeight
  const spaceAbove = absoluteY - menuHeight

  let top

  if (spaceBelow >= menuHeight + 10 || spaceBelow > spaceAbove) {
    top = absoluteY + danmakuHeight + 5
  } else {
    top = absoluteY - menuHeight - 5
  }

  let right = window.innerWidth - absoluteX - danmakuWidth - 10
  if (right < 10) {
    right = 10
  }

  return {
    top: top + 'px',
    right: right + 'px'
  }
}

function shareUrl() {
  if (channels.value.length === 0) {
    alert('请先添加频道')
    return
  }
  
  const channelStr = channels.value
    .map(ch => `${ch.platform}_${ch.id}`)
    .join(',')
  const shareCode = btoa(channelStr)
  
  const url = `${window.location.origin}/multiview?c=${shareCode}`
  
  navigator.clipboard.writeText(url).then(() => {
    alert('分享链接已复制到剪贴板')
  }).catch(() => {
    prompt('分享链接：', url)
  })
}

function connectWs(videoId) {
  if (wsConnections.value[videoId]) {
    return
  }
  
  const ws = new WebSocket(`${WS_BASE}/ws/danmaku/${videoId}`)
  
  ws.onopen = () => {
    console.log(`WebSocket connected: ${videoId}`)
    delete reconnectTimers.value[videoId]
  }
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'danmaku' && data.data) {
        addDanmakuMessages(videoId, data.data)
      }
    } catch (e) {
      console.error('Failed to parse danmaku message:', e)
    }
  }
  
  ws.onclose = () => {
    console.log(`WebSocket closed: ${videoId}`)
    delete wsConnections.value[videoId]
    
    if (showDanmaku.value) {
      scheduleReconnect(videoId)
    }
  }
  
  ws.onerror = (error) => {
    console.error(`WebSocket error for ${videoId}:`, error)
  }
  
  wsConnections.value[videoId] = ws
}

function disconnectWs(videoId) {
  const ws = wsConnections.value[videoId]
  if (ws) {
    ws.close()
    delete wsConnections.value[videoId]
  }
  
  if (reconnectTimers.value[videoId]) {
    clearTimeout(reconnectTimers.value[videoId])
    delete reconnectTimers.value[videoId]
  }
}

function scheduleReconnect(videoId) {
  if (reconnectTimers.value[videoId]) {
    return
  }
  
  reconnectTimers.value[videoId] = setTimeout(() => {
    delete reconnectTimers.value[videoId]
    if (showDanmaku.value) {
      connectWs(videoId)
    }
  }, 3000)
}

function addDanmakuMessages(videoId, messages) {
  const idx = channels.value.findIndex(ch => ch.id === videoId)
  if (idx === -1) return

  const canvas = danmakuCanvases.value[idx]
  if (!canvas) return

  const queue = danmakuQueues.value[idx] || []
  const tracks = trackStates.value[idx]
  if (!tracks) return

  const fontSize = getFontSize()
  if (!window._measureCtx) {
    window._measureCtx = document.createElement('canvas').getContext('2d')
  }
  window._measureCtx.font = `${fontSize}px "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif`
  
  messages.forEach(msg => {
    const userId = msg.user_id || ''
    const displayName = msg.user_display_name || ''
    
    const userRule = getUserRule(userId, displayName)
    if (userRule && userRule.action === 'block') {
      return
    }
    
    if (msg.message_type === 'sticker' && msg.sticker_url) {
      queue.push({
        message_type: 'sticker',
        sticker_url: msg.sticker_url,
        alt_text: msg.alt_text || 'Sticker',
        x: 800,
        y: 50 + Math.random() * 300,
        loaded: false
      })
      
      if (!stickerImages.value[msg.sticker_url]) {
        const img = new Image()
        img.onload = () => {
          stickerImages.value[msg.sticker_url] = img
          queue.forEach(m => {
            if (m.sticker_url === msg.sticker_url) {
              m.loaded = true
            }
          })
        }
        img.onerror = () => {
          stickerImages.value[msg.sticker_url] = null
        }
        img.src = msg.sticker_url
      }
      return
    }
    
    const text = msg.comment || msg.message || ''
    if (!text) return

    const textWidth = window._measureCtx.measureText(text).width
    const baseSpeed = danmakuSettings.value.global.speed || 2
    const speed = baseSpeed + Math.random() * 1.2

    let targetTrack = -1
    for (let t = 0; t < tracks.length; t++) {
      if (tracks[t].tailX <= canvas.width) {
        targetTrack = t
        break
      }
    }

    if (targetTrack === -1) {
      targetTrack = Math.floor(Math.random() * tracks.length)
    }

    tracks[targetTrack].tailX = canvas.width + textWidth + 20

    let danmakuColor = danmakuSettings.value.global.color || '#ffffff'
    let isHighlighted = false
    let fontWeight = 'normal'
    
    if (userRule && userRule.action === 'highlight') {
      danmakuColor = userRule.color || danmakuColor
      isHighlighted = true
      fontWeight = 'bold'
    }
    
    queue.push({
      content: text,
      color: isHighlighted ? danmakuColor : randomColor(),
      x: canvas.width + 10,
      trackIdx: targetTrack,
      speed,
      width: textWidth,
      isHighlighted,
      fontWeight,
      userId,
      displayName
    })
  })

  danmakuQueues.value[idx] = queue
}

function randomColor() {
  const colors = ['#ffffff', '#ffb3ba', '#ffdfba', '#ffffba', '#baffc9', '#bae1ff']
  return colors[Math.floor(Math.random() * colors.length)]
}
  
  danmakuQueues.value[idx] = queue
}

onMounted(() => {
  initHitboxPool()
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
    } catch (e) {
      console.error('Failed to parse share code:', e)
    }
  }
  
  const saved = localStorage.getItem('multiview_channels')
  if (saved) {
    try {
      channels.value = JSON.parse(saved)
    } catch (e) {
      console.error('Failed to restore channels:', e)
    }
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
    const canvas = danmakuCanvases.value[idx]
    if (!canvas) return

    const wrapper = canvas.parentElement
    if (!wrapper) return

    const rect = wrapper.getBoundingClientRect()
    if (rect.width > 0 && rect.height > 0) {
      canvas.width = rect.width
      canvas.height = rect.height
      initTrackState(idx, rect.height)
    }

    danmakuQueues.value[idx] = danmakuQueues.value[idx] || []

    if (ch.platform === 'youtube') {
      connectWs(ch.id)
    }

    startDanmakuLoop(idx)
  })
  
  window.addEventListener('resize', handleResize)
}

function handleResize() {
  if (!showDanmaku.value) return
  
  channels.value.forEach((ch, idx) => {
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
  
  Object.keys(wsConnections.value).forEach(videoId => {
    disconnectWs(videoId)
  })
}

function startDanmakuLoop(idx) {
  const renderTimer = setInterval(() => {
    renderDanmaku(idx)
  }, 30)
  danmakuTimers.value.push(renderTimer)
}

function renderDanmaku(idx) {
  const canvas = danmakuCanvases.value[idx]
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  if (canvas.width === 0 || canvas.height === 0) return

  const queue = danmakuQueues.value[idx]
  if (!queue || queue.length === 0) {
    hoveredDanmaku.value.show = false
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    return
  }

  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const fontSize = getFontSize()
  const opacity = danmakuSettings.value.global.opacity || 1
  const font = `${fontSize}px "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif`
  ctx.font = font
  ctx.textBaseline = 'top'
  ctx.globalAlpha = opacity

  const y0 = TRACK_TOP_OFFSET
  const trackHeight = getTrackHeight()
  const tracks = trackStates.value[idx]

  const activeHitboxIds = new Set()

  for (let i = queue.length - 1; i >= 0; i--) {
    const msg = queue[i]
    
    const userId = msg.userId || ''
    const displayName = msg.displayName || ''
    const hasUser = userId || displayName

    if (!msg.paused) {
      msg.x -= msg.speed
    }

    if (msg.x + msg.width < 0) {
      if (msg.hitbox) {
        returnHitboxToPool(msg.hitbox)
        msg.hitbox = null
      }
      queue.splice(i, 1)
      continue
    }

    const y = y0 + msg.trackIdx * trackHeight

    if (hasUser) {
      if (!msg.hitbox) {
        msg.hitbox = getHitboxFromPool()
      }
      
      if (msg.hitbox) {
        msg.hitbox.el.dataset.userId = userId
        msg.hitbox.el.dataset.displayName = displayName
        msg.hitbox.el.dataset.idx = String(idx)
        
        const wrapper = canvas.parentElement
        if (wrapper) {
          updateHitboxPosition(msg.hitbox, msg.x, y, msg.width || 100, trackHeight)
          
          const layer = hitboxLayers.value[idx]
          if (layer && msg.hitbox.el.parentElement !== layer) {
            layer.appendChild(msg.hitbox.el)
          }
        }
        
        activeHitboxIds.add(msg.hitbox)
      }
    }

    ctx.fillStyle = msg.color
    ctx.fillText(msg.content, msg.x, y)
  }

  hitboxPool.value.forEach(hitbox => {
    if (hitbox.inUse && hitbox.idx === idx && !activeHitboxIds.has(hitbox)) {
      returnHitboxToPool(hitbox)
    }
  })

  ctx.globalAlpha = 1
}

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  stopDanmaku()
  hitboxPool.value.forEach(h => {
    if (h.el && h.el.parentElement) {
      h.el.parentElement.removeChild(h.el)
    }
  })
  hitboxPool.value = []
})
</script>