// frontend/src/stores/stream.ts  ← 完整替换
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
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

export type StreamStatus = 'live' | 'upcoming' | 'archive' | 'offline'

export const useStreamStore = defineStore('stream', () => {
  const streams = ref<Stream[]>([])
  const currentStatus = ref<StreamStatus>('live')
  const loading = ref(false)
  const error = ref<string | null>(null)

  const liveStreams = computed(() => 
    streams.value.filter(s => s.status === 'live')
  )
  const upcomingStreams = computed(() => 
    streams.value.filter(s => s.status === 'upcoming')
  )
  const archiveStreams = computed(() => 
    streams.value.filter(s => s.status === 'archive')
  )

  async function fetchStreams(status?: StreamStatus) {
    loading.value = true
    error.value = null
    try {
      const params = status ? { status } : {}
      const { data } = await streamApi.getAllStreams(params)
      streams.value = data
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      error.value = msg
      console.error('Failed to fetch streams:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchLiveStreams() {
    await fetchStreams('live')
  }

  async function setStatus(status: StreamStatus) {
    currentStatus.value = status
    await fetchStreams(status)
  }

  const currentStreams = computed(() => {
    switch (currentStatus.value) {
      case 'live': return liveStreams.value
      case 'upcoming': return upcomingStreams.value
      case 'archive': return archiveStreams.value
      default: return streams.value
    }
  })

  return { 
    streams, 
    liveStreams,
    upcomingStreams,
    archiveStreams,
    currentStatus,
    currentStreams,
    loading, 
    error, 
    fetchLiveStreams,
    fetchStreams,
    setStatus
  }
})