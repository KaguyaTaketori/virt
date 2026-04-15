import { useMutation, useQueryClient } from '@tanstack/vue-query'
import type { UseMutationOptions } from '@tanstack/vue-query'
import type { Channel, ChannelCreate, Organization } from '@/types'
import { channelApi, orgApi, userChannelApi } from '@/api'

export function useCreateChannel(
  options?: Omit<UseMutationOptions<Channel, Error, Partial<ChannelCreate>>, 'mutationFn'>,
) {
  const queryClient = useQueryClient()

  return useMutation<Channel, Error, Partial<ChannelCreate>>({
    mutationFn: async (channelData) => {
      const { data } = await channelApi.create(channelData)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
    },
    ...options,
  })
}

export function useUpdateChannel(
  options?: Omit<UseMutationOptions<Channel, Error, { id: string; data: Partial<Channel> }>, 'mutationFn'>,
) {
  const queryClient = useQueryClient()

  return useMutation<Channel, Error, { id: string; data: Partial<Channel> }>({
    mutationFn: async ({ id, data }) => {
      const { data: result } = await channelApi.update(id, data)
      return result
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
      queryClient.invalidateQueries({ queryKey: ['channel', variables.id] })
    },
    ...options,
  })
}

export function useDeleteChannel(
  options?: Omit<UseMutationOptions<void, Error, string>, 'mutationFn'>,
) {
  const queryClient = useQueryClient()

  return useMutation<void, Error, string>({
    mutationFn: async (channelId) => {
      await channelApi.delete(channelId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
    },
    ...options,
  })
}

export function useLikeChannel(
  options?: Omit<UseMutationOptions<void, Error, string>, 'mutationFn'>,
) {
  const queryClient = useQueryClient()

  return useMutation<void, Error, string>({
    mutationFn: async (channelId) => {
      await userChannelApi.like(channelId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
    },
    ...options,
  })
}

export function useUnlikeChannel(
  options?: Omit<UseMutationOptions<void, Error, string>, 'mutationFn'>,
) {
  const queryClient = useQueryClient()

  return useMutation<void, Error, string>({
    mutationFn: async (channelId) => {
      await userChannelApi.unlike(channelId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
    },
    ...options,
  })
}

export function useBlockChannel(
  options?: Omit<UseMutationOptions<void, Error, string>, 'mutationFn'>,
) {
  const queryClient = useQueryClient()

  return useMutation<void, Error, string>({
    mutationFn: async (channelId) => {
      await userChannelApi.block(channelId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
    },
    ...options,
  })
}

export function useUnblockChannel(
  options?: Omit<UseMutationOptions<void, Error, string>, 'mutationFn'>,
) {
  const queryClient = useQueryClient()

  return useMutation<void, Error, string>({
    mutationFn: async (channelId) => {
      await userChannelApi.unblock(channelId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
    },
    ...options,
  })
}

export function useCreateOrganization(
  options?: Omit<UseMutationOptions<Organization, Error, Partial<Organization>>, 'mutationFn'>,
) {
  const queryClient = useQueryClient()

  return useMutation<Organization, Error, Partial<Organization>>({
    mutationFn: async (orgData) => {
      const { data } = await orgApi.create(orgData)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] })
    },
    ...options,
  })
}

export function useUpdateOrganization(
  options?: Omit<UseMutationOptions<Organization, Error, { id: number; data: Partial<Organization> }>, 'mutationFn'>,
) {
  const queryClient = useQueryClient()

  return useMutation<Organization, Error, { id: number; data: Partial<Organization> }>({
    mutationFn: async ({ id, data }) => {
      const { data: result } = await orgApi.update(id, data)
      return result
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] })
    },
    ...options,
  })
}

export function useDeleteOrganization(
  options?: Omit<UseMutationOptions<void, Error, number>, 'mutationFn'>,
) {
  const queryClient = useQueryClient()

  return useMutation<void, Error, number>({
    mutationFn: async (orgId) => {
      await orgApi.delete(orgId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] })
    },
    ...options,
  })
}