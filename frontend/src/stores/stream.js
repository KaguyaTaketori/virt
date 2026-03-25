import { defineStore } from 'pinia'
import { ref } from 'vue'
import { streamApi } from '../api'

export const useStreamStore = defineStore('stream', () => {
  const liveStreams = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchLiveStreams() {
    loading.value = true
    error.value = null
    try {
      const { data } = await streamApi.getLiveStreams()
      liveStreams.value = data
    } catch (err) {
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