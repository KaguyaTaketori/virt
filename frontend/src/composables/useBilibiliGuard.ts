import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import type { Stream, Channel, BilibiliGuard } from '@/types'


export function useBilibiliGuard(): BilibiliGuard {
  const authStore = useAuthStore()

  const canAccess = computed(() => authStore.canAccessBilibili)

  function filterStreams(streams: Stream[]): Stream[] {
    if (canAccess.value) return streams
    return streams.filter((s) => s.platform !== 'bilibili')
  }

  function filterChannels(channels: Channel[]): Channel[] {
    if (canAccess.value) return channels
    return channels.filter((c) => c.platform !== 'bilibili')
  }

  const platformOptions = computed<{ label: string; value: string }[]>(() => {
    const base = [{ label: 'YouTube', value: 'youtube' }]
    if (canAccess.value) {
      return [{ label: 'Bilibili', value: 'bilibili' }, ...base]
    }
    return base
  })

  return { canAccess, filterStreams, filterChannels, platformOptions }
}