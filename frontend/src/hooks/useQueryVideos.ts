import { useQuery, useQueries } from '@tanstack/vue-query'
import type { UseQueryOptions } from '@tanstack/vue-query'
import type { ComputedRef, Ref } from 'vue'
import type { Video, PaginatedVideos } from '@/types'
import { channelApi } from '@/api'

export function useChannelVideos(
  channelId: Ref<number> | ComputedRef<number>,
  options?: {
    page?: number
    pageSize?: number
    status?: string
  } & Omit<UseQueryOptions<PaginatedVideos, Error>, 'queryKey' | 'queryFn'>,
) {
  const {
    page = 1,
    pageSize = 24,
    status,
    ...queryOptions
  } = options || {}

  return useQuery<PaginatedVideos, Error>({
    queryKey: ['videos', channelId, page, pageSize, status],
    queryFn: async () => {
      const { data } = await channelApi.getVideos(
        channelId.value,
        page,
        pageSize,
        status,
      )
      return data
    },
    enabled: !!channelId.value,
    staleTime: 120_000,
    ...queryOptions,
  })
}

export function useMultiStatusVideos(
  channelId: Ref<number> | ComputedRef<number>,
  statuses: string[],
  options?: Omit<UseQueryOptions<PaginatedVideos[], Error>, 'queryKey' | 'queryFn'>,
) {
  return useQueries({
    queries: (statuses || []).map((status) => ({
      queryKey: ['videos', channelId, status],
      queryFn: async () => {
        const { data } = await channelApi.getVideos(channelId.value, 1, 24, status)
        return data
      },
      enabled: !!channelId.value,
      staleTime: 120_000,
      ...options,
    })),
  })
}

export function useAdminVideos(
  params: {
    channel_id: number
    status?: string | null
    duration_min?: number | null
    duration_max?: number | null
    page?: number
    page_size?: number
  },
  options?: Omit<UseQueryOptions<PaginatedVideos, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<PaginatedVideos, Error>({
    queryKey: ['admin', 'videos', params],
    queryFn: async () => {
      const { data } = await channelApi.getVideos(
        params.channel_id,
        params.page,
        params.page_size,
        params.status,
      )
      return data
    },
    staleTime: 60_000,
    ...options,
  })
}