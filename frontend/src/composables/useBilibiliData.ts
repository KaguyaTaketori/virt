import { ref } from 'vue'
import { channelApi } from '@/api'
import type { BilibiliInfoData, BilibiliVideo, BilibiliDynamic } from '@/types'


export interface ContentNode {
  type: 'text' | 'emoji' | 'at'
  text: string
  url?: string
  rid?: string
}

export function useBilibiliData() {
  const dynamics = ref<BilibiliDynamic[]>([])
  const videos = ref<BilibiliVideo[]>([])
  const info = ref<BilibiliInfoData | null>(null)
  const nextOffset = ref('')
  const loading = ref(false)
  const hasMore = ref(true)

  async function fetchInfo(channelId: string) {
    loading.value = true
    try {
      const { data } = await channelApi.getBilibiliInfo(channelId)
      info.value = data
    } catch (e) {
      console.error('Failed to fetch Bilibili info:', e)
    } finally {
      loading.value = false
    }
  }

  async function fetchVideos(channelId: string, page = 1, pageSize = 30) {
    loading.value = true
    try {
      const { data } = await channelApi.getBilibiliVideos(channelId, page, pageSize)
      videos.value = data.videos
    } catch (e) {
      console.error('Failed to fetch Bilibili videos:', e)
    } finally {
      loading.value = false
    }
  }

  async function fetchDynamics(channelId: string, offset = '', append = false) {
    if (loading.value) return
    loading.value = true
    try {
      const { data } = await channelApi.getBilibiliDynamics(channelId, offset, 12)
      if (!append) {
        dynamics.value = data.dynamics
      } else {
        dynamics.value = [...dynamics.value, ...data.dynamics]
      }
      nextOffset.value = data.next_offset || ''
      hasMore.value = !!data.next_offset
    } catch (e) {
      console.error('Failed to fetch Bilibili dynamics:', e)
    } finally {
      loading.value = false
    }
  }

  function loadMoreDynamics(channelId: string) {
    if (!hasMore.value || !nextOffset.value) return
    fetchDynamics(channelId, nextOffset.value, true)
  }

  function reset() {
    dynamics.value = []
    videos.value = []
    info.value = null
    nextOffset.value = ''
    hasMore.value = true
  }

  return {
    dynamics,
    videos,
    info,
    nextOffset,
    loading,
    hasMore,
    fetchInfo,
    fetchVideos,
    fetchDynamics,
    loadMoreDynamics,
    reset,
  }
}