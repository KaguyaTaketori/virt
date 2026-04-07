import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { streamApi } from '@/api'
import type { Stream, StreamStatus } from '@/types'

export type { Stream, StreamStatus }

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