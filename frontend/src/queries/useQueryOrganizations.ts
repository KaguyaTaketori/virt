import { useQuery } from '@tanstack/vue-query'
import type { UseQueryOptions } from '@tanstack/vue-query'
import type { Organization } from '@/types'
import { orgApi } from '@/api'

export function useOrganizations(
  options?: Omit<UseQueryOptions<Organization[], Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<Organization[], Error>({
    queryKey: ['organizations'],
    queryFn: async () => {
      const { data } = await orgApi.getAll()
      return data
    },
    staleTime: 5 * 60 * 1000,
    ...options,
  })
}

export function useOrganization(
  orgId: number,
  options?: Omit<UseQueryOptions<Organization, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<Organization, Error>({
    queryKey: ['organization', orgId],
    queryFn: async () => {
      const { data } = await orgApi.get(orgId)
      return data
    },
    enabled: !!orgId,
    staleTime: 5 * 60 * 1000,
    ...options,
  })
}