// frontend/src/stores/stream.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { streamApi } from '../api'

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
  scheduled_at: string | null
  channel_name: string | null
  channel_avatar: string | null
  channel_avatar_shape?: 'circle' | 'square'
  org_id?: number | null
}

export type StreamStatus = 'live' | 'upcoming' | 'archive' | 'offline'

export const useStreamStore = defineStore('stream', () => {
  const streams = ref<Stream[]>([])
  const currentStatus = ref<StreamStatus>('live')
  const currentOrgId = ref<number | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  // 记录上次拉取时间，避免频繁重复请求
  const lastFetchedAt = ref<number>(0)
  const CACHE_TTL = 60_000  // 1 分钟内不重复拉取

  // 按 status 分组
  const liveStreams    = computed(() => streams.value.filter(s => s.status === 'live'))
  const upcomingStreams = computed(() => streams.value.filter(s => s.status === 'upcoming'))
  const archiveStreams  = computed(() => streams.value.filter(s => s.status === 'archive'))
  const offlineStreams  = computed(() => streams.value.filter(s => s.status === 'offline'))

  // 当前 tab 的流（叠加 org 过滤）
  const currentStreams = computed(() => {
    let base: Stream[]
    switch (currentStatus.value) {
      case 'live':     base = liveStreams.value;     break
      case 'upcoming': base = upcomingStreams.value; break
      case 'archive':  base = archiveStreams.value;  break
      case 'offline':  base = offlineStreams.value;  break
      default:         base = streams.value
    }
    if (currentOrgId.value === null) return base
    return base.filter(s => {
      // org_id 需要从 channel 信息里带过来，见后端改动
      return (s as any).org_id === currentOrgId.value
    })
  })

  async function fetchStreams(force = false) {
    const now = Date.now()
    if (!force && now - lastFetchedAt.value < CACHE_TTL) return

    loading.value = true
    error.value = null
    try {
      // 一次拉取全部状态，后端不传 status 参数
      const { data } = await streamApi.getAllStreams()
      streams.value = data
      lastFetchedAt.value = Date.now()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      error.value = msg
      console.error('Failed to fetch streams:', err)
    } finally {
      loading.value = false
    }
  }

  // 保留这个方法供外部调用（强制刷新）
  async function fetchLiveStreams() {
    await fetchStreams(true)
  }

  function setStatus(status: StreamStatus) {
    currentStatus.value = status
    // 不再触发网络请求，纯前端切换
  }

  function setOrg(orgId: number | null) {
    currentOrgId.value = orgId
  }

  return {
    streams,
    liveStreams,
    upcomingStreams,
    archiveStreams,
    offlineStreams,
    currentStatus,
    currentOrgId,
    currentStreams,
    loading,
    error,
    fetchStreams,
    fetchLiveStreams,
    setStatus,
    setOrg,
  }
})