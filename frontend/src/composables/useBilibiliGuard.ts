// frontend/src/composables/useBilibiliGuard.ts（新增文件）
// ─────────────────────────────────────────────────────────────────────────────
// 修复 [低] Bilibili 权限判断逻辑重复：
//   原代码在 Home.vue / Channels.vue / SplitPaneNode.vue / AdminChannels.vue
//   四处分别写 authStore.canAccessBilibili 过滤逻辑。
//
// 修复后：统一 composable，一处修改全局生效。
//
// 使用方式：
//   const { filterStreams, filterChannels, canAccess } = useBilibiliGuard()
//   const visible = filterStreams(allStreams)       // 过滤流列表
//   const channels = filterChannels(allChannels)   // 过滤频道列表
//   if (!canAccess.value) { ... }                  // 访问控制判断
// ─────────────────────────────────────────────────────────────────────────────

import { computed } from 'vue'
import type { ComputedRef } from 'vue'
import { useAuthStore } from '@/stores/auth'
import type { Stream, Channel, BilibiliGuard } from '@/types'

export type { BilibiliGuard }

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