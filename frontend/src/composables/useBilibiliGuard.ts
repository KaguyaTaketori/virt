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

import { computed, type ComputedRef } from 'vue'
import { useAuthStore } from '@/stores/auth'
import type { Stream } from '@/stores/stream'
import type { Channel } from '@/api'

interface BilibiliGuard {
  /** 当前用户是否有 Bilibili 访问权限 */
  canAccess: ComputedRef<boolean>
  /**
   * 过滤流列表：无权限时移除 bilibili 平台的流
   * 用于替代 Home.vue 中的 `streams.filter(s => s.platform !== 'bilibili')`
   */
  filterStreams: (streams: Stream[]) => Stream[]
  /**
   * 过滤频道列表：无权限时移除 bilibili 平台的频道
   * 用于替代 Channels.vue / AdminChannels.vue 中的 `channel.platform !== 'bilibili'`
   */
  filterChannels: (channels: Channel[]) => Channel[]
  /**
   * 平台选项列表（包含/排除 Bilibili 的 select options）
   * 用于替代 AdminChannels.vue / Channels.vue 中的 platformOptions computed
   */
  platformOptions: ComputedRef<{ label: string; value: string }[]>
}

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