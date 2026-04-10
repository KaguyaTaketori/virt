import { useQuery, useQueries, type UseQueryOptions } from '@tanstack/vue-query'
import { computed, toValue, type ComputedRef, type Ref } from 'vue'
import type { PaginatedVideos } from '@/types'
import { channelApi } from '@/api'

type MaybeRefOrGetter<T> = T | Ref<T> | ComputedRef<T> | (() => T)

// 1. 定义我们自己的参数接口
interface ChannelVideoParams {
  page?: MaybeRefOrGetter<number>
  pageSize?: MaybeRefOrGetter<number>
  status?: MaybeRefOrGetter<string | string[] | undefined>
}

// 2. 显式合并常用的 TanStack Query 选项
// 这样可以避开 Omit 在联合类型上的 Bug
export interface UseChannelVideosOptions extends ChannelVideoParams {
  enabled?: MaybeRefOrGetter<boolean>
  staleTime?: MaybeRefOrGetter<number>
  gcTime?: MaybeRefOrGetter<number>
  refetchOnWindowFocus?: MaybeRefOrGetter<boolean | "always">
  // 如果需要其他选项，可以继续添加，或者使用 [key: string]: any
}

export function useChannelVideos(
  channelId: MaybeRefOrGetter<number | undefined>,
  options: UseChannelVideosOptions = {}
) {
  return useQuery<PaginatedVideos, Error>({
    // 关键：queryKey 必须响应式地包含所有查询参数
    queryKey: [
      'videos', 
      () => toValue(channelId), 
      () => ({
        page: toValue(options.page),
        pageSize: toValue(options.pageSize),
        status: toValue(options.status)
      })
    ],
    
    queryFn: async () => {
      const id = toValue(channelId)
      if (!id) throw new Error('Channel ID is required')
      
      const { data } = await channelApi.getVideos(
        id,
        toValue(options.page) ?? 1,
        toValue(options.pageSize) ?? 24,
        toValue(options.status) as string, // 后端通常接受字符串
      )
      return data
    },

    // 默认启用逻辑：ID 存在且没有被外部手动禁用
    enabled: computed(() => {
      const idValid = !!toValue(channelId)
      const enabledOpt = toValue(options.enabled)
      return idValid && enabledOpt !== false
    }),

    staleTime: toValue(options.staleTime) ?? 120_000,
    
    // 展开其余选项
    ...options as any
  })
}

export function useMultiStatusVideos(
  channelId: MaybeRefOrGetter<number>,
  statuses: MaybeRefOrGetter<string[]>,
  options?: Omit<UseQueryOptions<PaginatedVideos, Error>, 'queryKey' | 'queryFn'>,
) {
  // 使用 computed 动态生成 queries 配置数组
  const queriesOptions = computed(() => {
    const id = toValue(channelId)
    const statusList = toValue(statuses) || []
    
    return statusList.map((status) => ({
      queryKey: ['videos', id, status],
      queryFn: async () => {
        const { data } = await channelApi.getVideos(id, 1, 24, status)
        return data
      },
      enabled: !!id,
      staleTime: 120_000,
      ...options,
    }))
  })

  return useQueries({
    queries: queriesOptions,
  })
}

export function useAdminVideos(
  params: MaybeRefOrGetter<{
    channel_id: number
    status?: string
    duration_min?: number | null
    duration_max?: number | null
    page?: number
    page_size?: number
  }>,
  options?: Omit<UseQueryOptions<PaginatedVideos, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<PaginatedVideos, Error>({
    // 监听整个 params 对象的变化
    queryKey: ['admin', 'videos', () => toValue(params)],
    queryFn: async () => {
      const p = toValue(params)
      const { data } = await channelApi.getVideos(
        p.channel_id,
        p.page,
        p.page_size,
        p.status,
      )
      return data
    },
    staleTime: 60_000,
    ...options,
  })
}