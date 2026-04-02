import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { streamApi } from '@/api'

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
  const currentStatus = ref<StreamStatus>('live')
  const currentOrgId = ref<number | null>(null)

  const { data: streams, isLoading: loading, error, refetch } = useQuery({
    queryKey: ['streams'],
    queryFn: async () => {
      const { data } = await streamApi.getAllStreams()
      return data as Stream[]
    },
    staleTime: 60_000,
  })

  const liveStreams = computed(() => streams.value?.filter(s => s.status === 'live') ?? [])
  const upcomingStreams = computed(() => streams.value?.filter(s => s.status === 'upcoming') ?? [])
  const archiveStreams = computed(() => streams.value?.filter(s => s.status === 'archive') ?? [])
  const offlineStreams = computed(() => streams.value?.filter(s => s.status === 'offline') ?? [])

  const currentStreams = computed(() => {
    let base: Stream[]
    switch (currentStatus.value) {
      case 'live':     base = liveStreams.value;     break
      case 'upcoming': base = upcomingStreams.value; break
      case 'archive':  base = archiveStreams.value;  break
      case 'offline':  base = offlineStreams.value;  break
      default:         base = streams.value ?? []
    }
    if (currentOrgId.value === null) return base
    return base.filter(s => (s as any).org_id === currentOrgId.value)
  })

  async function fetchStreams() {
    await refetch()
  }

  async function fetchLiveStreams() {
    await refetch()
  }

  function setStatus(status: StreamStatus) {
    currentStatus.value = status
  }

  function setOrg(orgId: number | null) {
    currentOrgId.value = orgId
  }

  return {
    streams: computed(() => streams.value ?? []),
    liveStreams,
    upcomingStreams,
    archiveStreams,
    offlineStreams,
    currentStatus,
    currentOrgId,
    currentStreams,
    loading: computed(() => loading.value),
    error: computed(() => error.value?.message ?? null),
    fetchStreams,
    fetchLiveStreams,
    setStatus,
    setOrg,
  }
})