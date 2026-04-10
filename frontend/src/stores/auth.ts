import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { QueryClient } from '@tanstack/vue-query'
import type { User } from '@/types'
import { authApi } from '@/api'
import router from '@/router'
import { ROLES, PERMISSIONS } from '@/constants/auth'

export type { User }

let _sharedQueryClient: QueryClient | null = null

export function setSharedQueryClient(qc: QueryClient) {
  _sharedQueryClient = qc
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!token.value)

  const hasRole = (role: string): boolean =>
    user.value?.roles?.includes(role) ?? false

  const hasPermission = (perm: string): boolean =>
    user.value?.permissions?.includes(perm) ?? false

  const isSuperAdmin = computed(() => hasRole(ROLES.SUPERADMIN))
  const isAdmin = computed(() => hasRole(ROLES.ADMIN) || isSuperAdmin.value)
  const isOperator = computed(() => hasRole(ROLES.OPERATOR) || isAdmin.value)
  const canAccessBilibili = computed(
    () => hasPermission(PERMISSIONS.BILIBILI_ACCESS) || isSuperAdmin.value,
  )

  async function login(username: string, password: string): Promise<boolean> {
    loading.value = true
    try {
      const res = await authApi.login(username, password)
      token.value = res.data.access_token
      localStorage.setItem('token', res.data.access_token)
      await fetchUserInfo()
      return true
    } catch {
      return false
    } finally {
      loading.value = false
    }
  }

  async function register(username: string, email: string, password: string): Promise<boolean> {
    loading.value = true
    try {
      await authApi.register({ username, email, password })
      return await login(username, password)
    } catch {
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchUserInfo(): Promise<void> {
    if (!token.value) return
    try {
      const res = await authApi.getUserInfo()
      user.value = res.data
    } catch (e: any) {
      if (e.response?.status === 401) {
        token.value = null
        user.value = null
        localStorage.removeItem('token')
        router.push('/')
      } else {
        console.error('Failed to fetch user info:', e)
      }
    }
  }

  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } catch (e) {
      console.error('Logout API failed:', e)
    }

    // 修复：通过 module-level 引用可靠地清空缓存，不依赖 hooks
    if (_sharedQueryClient) {
      _sharedQueryClient.clear()
    } else {
      console.warn('[auth] queryClient not injected, cache not cleared')
    }

    token.value = null
    user.value = null
    localStorage.removeItem('token')
    router.push('/')
  }

  async function init(): Promise<void> {
    if (token.value) await fetchUserInfo()
  }

  return {
    token, user, loading,
    isLoggedIn, isSuperAdmin, isAdmin, isOperator, canAccessBilibili,
    hasRole, hasPermission,
    login, register, logout, fetchUserInfo, init,
  }
})