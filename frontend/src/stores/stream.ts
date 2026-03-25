import { defineStore } from 'pinia'
import { ref } from 'vue'
import { streamApi } from '../api'

export interface Stream {
  id: number
  platform: string
  name: string
  url: string
  is_live: boolean
  thumbnail?: string
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
    } catch (err: any) {
      error.value = err.message
      console.error('Failed to fetch live streams:', err)
    } finally {
      loading.value = false
    }
  }

  return {
    liveStreams,
    loading,
    error,
    fetchLiveStreams
  }
})
