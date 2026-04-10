import { useQuery, useQueries } from '@tanstack/vue-query'
import type { UseQueryOptions } from '@tanstack/vue-query'
import type { ComputedRef, Ref } from 'vue'
import type { Stream } from '@/types'
import { streamApi, channelApi } from '@/api'
import type { Channel } from '@/types'

export type StreamQueryEnabled = ComputedRef<boolean> | Ref<boolean> | boolean

export function useLiveStreams(
  options?: Omit<UseQueryOptions<Stream[], Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<Stream[], Error>({
    queryKey: ['streams', 'live'],
    queryFn: async () => {
      const { data } = await streamApi.getLiveStreams()
      return data
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
    ...options,
  })
}

export function useAllStreams(
  params?: {
    platform?: string
    status?: string
    org_id?: number
  },
  options?: Omit<UseQueryOptions<Stream[], Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<Stream[], Error>({
    queryKey: ['streams', 'all', params],
    queryFn: async () => {
      const { data } = await streamApi.getAllStreams(params as Record<string, unknown>)
      return data
    },
    staleTime: 60_000,
    refetchInterval: 120_000,
    ...options,
  })
}

export function useStreamsByPlatform(
  platforms: string[],
  options?: Omit<UseQueryOptions<Stream[], Error>, 'queryKey' | 'queryFn'>,
) {
  const enabled = platforms && platforms.length > 0

  return useQueries({
    queries: (platforms || []).map((platform) => ({
      queryKey: ['streams', platform],
      queryFn: async () => {
        const { data } = await streamApi.getAllStreams({ platform })
        return data
      },
      staleTime: 60_000,
      refetchInterval: 120_000,
      enabled,
      ...options,
    })),
  })
}

export function useChannelStreams(
  channelId: Ref<number> | ComputedRef<number>,
  options?: Omit<UseQueryOptions<Stream[], Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<Stream[], Error>({
    queryKey: ['streams', channelId],
    queryFn: async () => {
      const { data } = await streamApi.getAllStreams({ channel_id: channelId.value })
      return data
    },
    enabled: !!channelId.value,
    staleTime: 30_000,
    refetchInterval: 60_000,
    ...options,
  })
}

export function useChannelInfo(
  channelId: Ref<number> | ComputedRef<number>,
  options?: Omit<UseQueryOptions<Channel, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<Channel, Error>({
    queryKey: ['channel', channelId],
    queryFn: async () => {
      const { data } = await channelApi.get(channelId.value)
      return data
    },
    enabled: !!channelId.value,
    staleTime: 300_000,
    ...options,
  })
}

export function useChannels(
  params?: {
    platform?: string
    is_active?: boolean
    org_id?: number
  },
  options?: Omit<UseQueryOptions<Channel[], Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<Channel[], Error>({
    queryKey: ['channels', params],
    queryFn: async () => {
      const { data } = await channelApi.getAll(params as Record<string, unknown>)
      return data
    },
    staleTime: 120_000,
    refetchInterval: 300_000,
    ...options,
  })
}