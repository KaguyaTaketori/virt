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
        <div v-if="!getEmbedUrl(ch)" class="flex items-center justify-center h-full text-gray-500">
          无效的嵌入链接
        </div>
      </div>
    </div>

    <div v-if="channels.length === 0" class="text-center py-12 text-gray-500">
      <p class="text-xl">添加频道开始多窗观看</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'

const newChannel = ref({
  platform: 'youtube',
  id: ''
})

const channels = ref([])
const showDanmaku = ref(false)
const danmakuCanvases = ref([])
const danmakuContexts = ref([])
const danmakuTimers = ref([])
const danmakuQueues = ref([])

const wsConnections = ref({})
const reconnectTimers = ref({})
const stickerImages = ref({})

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
  
  const queue = danmakuQueues.value[idx] || []
  
  messages.forEach(msg => {
    const content = msg.comment || msg.message || ''
    
    // 处理 sticker
    if (msg.message_type === 'sticker' && msg.sticker_url) {
      queue.push({
        message_type: 'sticker',
        sticker_url: msg.sticker_url,
        alt_text: msg.alt_text || 'Sticker',
        x: 800,
        y: 50 + Math.random() * 300,
        loaded: false
      })
      
      // 预加载 sticker 图片
      if (!stickerImages.value[msg.sticker_url]) {
        const img = new Image()
        img.onload = () => {
          stickerImages.value[msg.sticker_url] = img
          // 找到并更新该消息的状态
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
    
    // 处理普通文字消息
    if (!content) return
    
    const colors = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff', '#ffffff', '#ffaa00', '#aaff00', '#00aaff']
    const color = colors[Math.floor(Math.random() * colors.length)]
    
    queue.push({
      content,
      color,
      x: 800,
      y: 50 + Math.random() * 300
    })
  })
  
  danmakuQueues.value[idx] = queue
}

onMounted(() => {
  // 从 localStorage 恢复频道
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
    
    const rect = canvas.parentElement.getBoundingClientRect()
    canvas.width = rect.width
    canvas.height = rect.height
    
    const ctx = canvas.getContext('2d')
    danmakuContexts.value[idx] = { ctx, canvas, tracks: [] }
    danmakuQueues.value[idx] = []
    
    if (ch.platform === 'youtube') {
      connectWs(ch.id)
    }
    
    startDanmakuLoop(idx)
  })
  
  // 添加窗口大小变化监听
  window.addEventListener('resize', handleResize)
}

function handleResize() {
  if (!showDanmaku.value) return
  
  // 重新设置所有 canvas 尺寸
  channels.value.forEach((ch, idx) => {
    const canvas = danmakuCanvases.value[idx]
    if (!canvas) return
    
    const rect = canvas.parentElement.getBoundingClientRect()
    canvas.width = rect.width
    canvas.height = rect.height
    
    // 更新 context
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
  const { ctx } = danmakuContexts.value[idx] || {}
  const queue = danmakuQueues.value[idx]
  if (!ctx || !queue || queue.length === 0) return
  
  const canvas = danmakuCanvases.value[idx]
  if (!canvas) return
  
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.font = '20px sans-serif'
  ctx.textBaseline = 'top'
  
  for (let i = queue.length - 1; i >= 0; i--) {
    const msg = queue[i]
    msg.x -= 2
    if (msg.x < -200) {
      queue.splice(i, 1)
      continue
    }
    
    // 处理 sticker
    if (msg.message_type === 'sticker') {
      const img = stickerImages.value[msg.sticker_url]
      if (img) {
        // 绘制 sticker 图片 (50x50)
        ctx.drawImage(img, msg.x, msg.y, 50, 50)
      } else if (msg.loaded === false) {
        // 图片未加载，显示 alt 文字作为后备
        ctx.fillStyle = '#ffcc00'
        ctx.fillText(msg.alt_text || 'Sticker', msg.x, msg.y)
      }
      continue
    }
    
    // 普通文字消息
    ctx.fillStyle = msg.color || '#ffffff'
    ctx.fillText(msg.content || msg.message || '', msg.x, msg.y)
  }
}

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  stopDanmaku()
})
</script>