import { ref } from 'vue'
import type { Ref } from 'vue'
import type { Video, VideoFetchState, FetchConfig } from '@/types'
import { channelApi } from '@/api'

export type { Video, VideoFetchState, FetchConfig }


export function useChannelVideos(config: FetchConfig): VideoFetchState {
  const videos = ref<Video[]>([])
  const page = ref(1)
  const totalPages = ref(0)
  const loading = ref(false)

  const pageSize = config.pageSize ?? 24
  const statuses = Array.isArray(config.status) ? config.status : [config.status]

  async function fetch(channelId: number): Promise<void> {
    loading.value = true
    try {
      if (statuses.length === 1) {
        // 单状态：直接请求
        const { data } = await channelApi.getVideos(
          channelId,
          page.value,
          pageSize,
          statuses[0],
        )
        videos.value = data.videos as Video[]
        totalPages.value = data.total_pages
      } else {
        // 多状态：并发请求后合并
        const results = await Promise.all(
          statuses.map((s) =>
            channelApi.getVideos(channelId, page.value, pageSize, s),
          ),
        )
        const merged: Video[] = results.flatMap((r) => r.data.videos as Video[])
        videos.value = config.mergeSort ? merged.sort(config.mergeSort) : merged
        totalPages.value = Math.max(...results.map((r) => r.data.total_pages))
      }
    } catch (err) {
      console.error(`[useChannelVideos] fetch failed (status=${config.status}):`, err)
    } finally {
      loading.value = false
    }
  }

  function reset() {
    videos.value = []
    page.value = 1
    totalPages.value = 0
  }

  return { videos, page, totalPages, loading, fetch, reset }
}