<template>
  <div class="container mx-auto px-4 py-8">
    <div class="mb-8">
      <h1 class="text-3xl font-bold mb-2">直播列表</h1>
      <p class="text-gray-400">VTuber 频道直播状态</p>
    </div>

    <!-- 状态筛选标签 -->
    <div class="mb-6 flex flex-wrap gap-2">
      <button
        v-for="status in statuses"
        :key="status.value"
        @click="store.setStatus(status.value)"
        class="px-4 py-2 rounded-full transition"
        :class="store.currentStatus === status.value 
          ? 'bg-pink-600 text-white' 
          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'"
      >
        {{ status.label }}
        <span class="ml-1 text-xs opacity-70">
          ({{ getCount(status.value) }})
        </span>
      </button>
    </div>

    <div v-if="store.loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-pink-500"></div>
    </div>

    <div v-else-if="store.error" class="text-center py-12 text-red-400">
      <p>加载失败: {{ store.error }}</p>
      <button @click="store.fetchLiveStreams" class="mt-4 px-4 py-2 bg-pink-600 rounded hover:bg-pink-700">
        重试
      </button>
    </div>

    <div v-else-if="store.currentStreams.length === 0" class="text-center py-12 text-gray-500">
      <p class="text-xl">暂无数据</p>
      <p class="mt-2">{{ statusDesc }}</p>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
      <StreamCard
        v-for="(stream, index) in store.currentStreams"
        :key="stream.id ?? `stream-${index}`"
        :stream="stream"
        @click="(s) => openMultiView(s)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useStreamStore, type StreamStatus } from '../stores/stream'
import StreamCard from '../components/StreamCard.vue'

const store = useStreamStore()
const router = useRouter()

const statuses: { value: StreamStatus; label: string }[] = [
  { value: 'live', label: '直播中' },
  { value: 'upcoming', label: '预约' },
  { value: 'archive', label: '录播' },
  { value: 'offline', label: '离线' },
]

const statusDesc = computed(() => {
  switch (store.currentStatus) {
    case 'live': return '等待主播开播...'
    case 'upcoming': return '暂无预约直播'
    case 'archive': return '暂无录播'
    case 'offline': return '主播当前离线'
    default: return ''
  }
})

function getCount(status: StreamStatus) {
  switch (status) {
    case 'live': return store.liveStreams.length
    case 'upcoming': return store.upcomingStreams.length
    case 'archive': return store.archiveStreams.length
    default: return 0
  }
}

onMounted(() => {
  store.fetchStreams('live')
})

function openMultiView(stream) {
  if (!stream) return
  const platform = stream.platform
  const ids = stream.video_id || stream.channel_id
  if (!ids) return
  
  // 存储到 localStorage
  const channels = [{ platform, id: ids }]
  localStorage.setItem('multiview_channels', JSON.stringify(channels))
  
  router.push({ name: 'MultiView' })
}
</script>