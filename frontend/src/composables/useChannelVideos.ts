/**
 * frontend/src/composables/useChannelVideos.ts
 *
 * 问题 11 修复：ChannelDetail.vue 中 fetchVideos / fetchLiveVideos / fetchShortsVideos
 * 三个函数结构完全一致，仅 status 参数和目标 ref 不同，提取为统一 composable。
 */
import { ref, type Ref } from 'vue'
import { channelApi } from '@/api'

export interface Video {
  id: string
  title: string
  thumbnail_url: string | null
  duration: string | null
  view_count: number
  published_at: string | null
  status: string
}

export interface VideoFetchState {
  videos: Ref<Video[]>
  page: Ref<number>
  totalPages: Ref<number>
  loading: Ref<boolean>
  fetch: (channelId: number) => Promise<void>
  reset: () => void
}

interface FetchConfig {
  /** 单个状态字符串 或 多状态数组（多状态时自动合并结果） */
  status: string | string[]
  pageSize?: number
  /** 多状态合并后的排序函数，默认不排序 */
  mergeSort?: (a: Video, b: Video) => number
}

/**
 * 统一的频道视频拉取 composable。
 *
 * 使用示例：
 *
 *   // 普通视频（上传）
 *   const uploadVideos = useChannelVideos({ status: 'upload' })
 *   await uploadVideos.fetch(channelId)
 *
 *   // 直播 + 预约合并，预约优先
 *   const liveVideos = useChannelVideos({
 *     status: ['live', 'upcoming'],
 *     pageSize: 48,
 *     mergeSort: (a, b) => {
 *       if (a.status === 'upcoming' && b.status !== 'upcoming') return -1
 *       if (a.status !== 'upcoming' && b.status === 'upcoming') return 1
 *       return 0
 *     }
 *   })
 *
 *   // Shorts
 *   const shortsVideos = useChannelVideos({ status: 'short', pageSize: 48 })
 */
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