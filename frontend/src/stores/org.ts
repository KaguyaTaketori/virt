// frontend/src/stores/org.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { orgApi, type Organization } from '../api'

export const useOrgStore = defineStore('org', () => {
  const organizations = ref<Organization[]>([])
  const loading = ref(false)

  async function fetchOrganizations() {
    if (organizations.value.length > 0) return  // 已有数据不重复拉
    loading.value = true
    try {
      const { data } = await orgApi.getAll()
      organizations.value = data
    } catch (err) {
      console.error('Failed to fetch organizations:', err)
    } finally {
      loading.value = false
    }
  }

  return { organizations, loading, fetchOrganizations }
})