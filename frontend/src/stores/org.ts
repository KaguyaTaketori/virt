import { defineStore } from 'pinia'
import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { orgApi, type Organization } from '@/api'

export const useOrgStore = defineStore('org', () => {
  const { data, isLoading: loading } = useQuery({
    queryKey: ['organizations'],
    queryFn: async () => {
      const { data } = await orgApi.getAll()
      return data as Organization[]
    },
    staleTime: 5 * 60 * 1000,
  })

  const organizations = computed(() => data.value ?? [])

  async function fetchOrganizations() {
  }

  return { organizations, loading, fetchOrganizations }
})