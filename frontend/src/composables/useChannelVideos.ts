/**
 * @deprecated 此兼容层已被废弃，请直接使用 hooks/useQueryVideos。
 * 
 * 迁移示例（ChannelDetail.vue）：
 *   旧: const state = useChannelVideos({ status: 'upload', pageSize: 24 })
 *       await state.fetch(channelId)
 * 
 *   新: const { data, isLoading, refetch } = useChannelVideos(channelIdRef, { 
 *         status: 'upload', pageSize: 24 
 *       })
 */

import { ref } from 'vue'
import type { Video, VideoFetchState, FetchConfig } from '@/types'
import { channelApi } from '@/api'

// 保留接口向后兼容，但修复核心逻辑
export function useChannelVideos(config: FetchConfig): VideoFetchState {
  const videos = ref<Video[]>([])
  const page = ref(1)
  const totalPages = ref(0)
  const loading = ref(false)

  async function fetch(channelId: number): Promise<void> {
    if (!channelId) return
    loading.value = true
    try {
      const statuses = Array.isArray(config.status) ? config.status : [config.status]
      
      // 多状态合并请求
      const results = await Promise.all(
        statuses.map(status =>
          channelApi.getVideos(channelId, page.value, config.pageSize ?? 24, status)
            .then(r => r.data)
        )
      )
      
      let merged = results.flatMap(r => r.videos)
      if (config.mergeSort) {
        merged = merged.sort(config.mergeSort)
      }
      
      videos.value = merged
      // totalPages 取第一个结果的分页信息（单状态场景）
      totalPages.value = results[0]?.total_pages ?? 0
    } catch (err) {
      console.error('[useChannelVideos] fetch failed:', err)
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