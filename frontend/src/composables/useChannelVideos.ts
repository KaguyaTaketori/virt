/**
 * @deprecated 请使用 hooks/useQueryVideos 中的 useChannelVideos
 * 此文件保留用于向后兼容，新代码应使用 TanStack Query hooks
 */
import { ref, computed } from 'vue'
import type { Ref } from 'vue'
import type { Video, VideoFetchState, FetchConfig } from '@/types'
import { useChannelVideos as useTqChannelVideos } from '@/hooks'

export type { Video, VideoFetchState, FetchConfig }

export function useChannelVideos(config: FetchConfig): VideoFetchState {
  const channelId = computed(() => config.status as unknown as number)
  
  const { data, isLoading, error, refetch } = useTqChannelVideos(channelId, {
    page: 1,
    pageSize: config.pageSize ?? 24,
    status: Array.isArray(config.status) ? config.status[0] : config.status ?? undefined,
  })
  
  const videos = computed(() => data.value?.videos ?? [])
  const totalPages = computed(() => data.value?.total_pages ?? 0)
  const loading = isLoading

  async function fetch(channelId: number): Promise<void> {
    await refetch()
  }

  function reset() {
    // TanStack Query 会自动处理缓存失效
  }

  return { 
    videos: videos as unknown as Ref<Video[]>, 
    page: ref(1) as Ref<number>, 
    totalPages, 
    loading, 
    fetch, 
    reset 
  }
}