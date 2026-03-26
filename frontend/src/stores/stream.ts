// frontend/src/stores/stream.ts  ← 完整替换
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { streamApi } from '../api'

// 与后端 StreamResponse schema 严格对应
export interface Stream {
  id: number
  channel_id: number
  platform: 'youtube' | 'bilibili'
  video_id: string | null
  title: string | null
  thumbnail_url: string | null
  viewer_count: number
  status: 'live' | 'upcoming' | 'archive' | 'offline'
  started_at: string | null
  channel_name: string | null
  channel_avatar: string | null
}

export const useStreamStore = defineStore('stream', () => {
  const liveStreams = ref<Stream[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchLiveStreams() {
    loading.value = true
    error.value = null
    try {
      const { data } = await streamApi.getLiveStreams()
      liveStreams.value = data
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      error.value = msg
      console.error('Failed to fetch live streams:', err)
    } finally {
      loading.value = false
    }
  }

  return { liveStreams, loading, error, fetchLiveStreams }
})