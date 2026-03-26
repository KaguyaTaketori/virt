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
import { useRoute } from 'vue-router'

const route = useRoute()

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
const danmakuNextPageTokens = ref({})

const mockMessages = [
  { content: "你好可爱！", color: "#ff0000" },
  { content: "加油！", color: "#00ff00" },
  { content: "哈哈笑死了", color: "#0000ff" },
  { content: "dddd", color: "#ffff00" },
  { content: "前方高能！", color: "#ff00ff" },
  { content: "太强了", color: "#00ffff" },
  { content: "awsl", color: "#ffffff" },
  { content: "火钳刘明", color: "#ffaa00" },
  { content: "绝了", color: "#aaff00" },
  { content: "666", color: "#00aaff" },
]

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
    return `https://player.bilibili.com/player.html?roomid=${ch.id}&autoplay=1`
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
}

function removeChannel(idx) {
  channels.value.splice(idx, 1)
}

onMounted(() => {
  const { platform, ids } = route.params
  if (platform && ids) {
    const idList = ids.split(',')
    idList.forEach(id => {
      channels.value.push({ platform, id: id.trim() })
    })
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
    danmakuContexts.value[idx] = { ctx, tracks: [] }
    danmakuQueues.value[idx] = []
    danmakuNextPageTokens.value[idx] = null
    
    fetchDanmaku(idx)
    startDanmakuLoop(idx)
  })
}

function stopDanmaku() {
  danmakuTimers.value.forEach(t => clearInterval(t))
  danmakuTimers.value = []
  danmakuContexts.value = []
  danmakuQueues.value = []
}

function fetchDanmaku(idx) {
  const mockMsg = mockMessages[Math.floor(Math.random() * mockMessages.length)]
  const queue = danmakuQueues.value[idx] || []
  queue.push({ ...mockMsg, x: 800, y: 50 + Math.random() * 300 })
  danmakuQueues.value[idx] = queue
}

function startDanmakuLoop(idx) {
  const timer = setInterval(() => {
    fetchDanmaku(idx)
  }, 800)
  danmakuTimers.value[idx] = timer
  
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
    ctx.fillStyle = msg.color || '#ffffff'
    ctx.fillText(msg.content || msg.message || '', msg.x, msg.y)
  }
}

onUnmounted(() => {
  stopDanmaku()
})
</script>