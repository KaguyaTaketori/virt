<template>
  <div class="container mx-auto px-4 py-8">
    <div class="mb-8">
      <h1 class="text-3xl font-bold mb-2">当前直播</h1>
      <p class="text-gray-400">正在直播的 VTuber 频道</p>
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

    <div v-else-if="store.liveStreams.length === 0" class="text-center py-12 text-gray-500">
      <p class="text-xl">暂无直播</p>
      <p class="mt-2">等待主播开播...</p>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
      <StreamCard
        v-for="(stream, index) in store.liveStreams"
        :key="stream.id ?? `stream-${index}`"
        :stream="stream"
        @click="(s) => openMultiView(s)"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useStreamStore } from '../stores/stream'
import StreamCard from '../components/StreamCard.vue'

const store = useStreamStore()
const router = useRouter()

onMounted(() => {
  store.fetchLiveStreams()
})

function openMultiView(stream) {
  if (!stream) return
  const platform = stream.platform
  const ids = stream.video_id || stream.channel_id
  router.push({ 
    name: 'MultiViewIds', 
    params: { platform, ids } 
  })
}
</script>