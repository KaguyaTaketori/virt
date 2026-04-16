import { useQuery, useQueries, type UseQueryOptions } from '@tanstack/vue-query'
import { computed, toValue, type ComputedRef, type Ref } from 'vue'
import type { PaginatedVideos } from '@/types'
import { channelApi } from '@/api'

type MaybeRefOrGetter<T> = T | Ref<T> | ComputedRef<T> | (() => T)

interface ChannelVideoParams {
  page?: MaybeRefOrGetter<number>
  pageSize?: MaybeRefOrGetter<number>
  status?: MaybeRefOrGetter<string | string[] | undefined>
}

export interface UseChannelVideosOptions extends ChannelVideoParams {
  enabled?: MaybeRefOrGetter<boolean>
  staleTime?: MaybeRefOrGetter<number>
  gcTime?: MaybeRefOrGetter<number>
  refetchOnWindowFocus?: MaybeRefOrGetter<boolean | "always">
}

export function useChannelVideos(
  channelId: MaybeRefOrGetter<string | undefined>,
  options: UseChannelVideosOptions = {}
) {
  return useQuery<PaginatedVideos, Error>({
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
        toValue(options.status) as string,
      )
      return data
    },

    enabled: computed(() => {
      const idValid = !!toValue(channelId)
      const enabledOpt = toValue(options.enabled)
      return idValid && enabledOpt !== false
    }),

    staleTime: toValue(options.staleTime) ?? 120_000,
    
    ...options as any
  })
}

export function useMultiStatusVideos(
  channelId: MaybeRefOrGetter<string>,
  statuses: MaybeRefOrGetter<string[]>,
  options?: Omit<UseQueryOptions<PaginatedVideos, Error>, 'queryKey' | 'queryFn'>,
) {
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
    channel_id: string
    status?: string
    duration_min?: number | null
    duration_max?: number | null
    page?: number
    page_size?: number
  }>,
  options?: Omit<UseQueryOptions<PaginatedVideos, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<PaginatedVideos, Error>({
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