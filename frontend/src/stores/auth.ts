/**
 * frontend/src/stores/auth.ts（修复版）
 *
 * 问题 12 修复：logout 时可靠地清空 TanStack Query 缓存。
 *
 * 原问题：_getQueryClient() 使用懒加载 + try/catch 静默失败。
 * 若 logout 在组件 setup 生命周期之外被调用，useQueryClient() 会抛异常，
 * 导致 qc.clear() 从未执行，前一用户的数据对新用户短暂可见。
 *
 * 修复方案：
 *   在 main.ts 中创建 QueryClient 后，通过 setQueryClient() 注入到 store。
 *   store 不再直接调用 useQueryClient()（hooks 只能在 setup 中使用）。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { QueryClient } from '@tanstack/vue-query'
import { authApi } from '@/api'
import router from '@/router'

interface User {
  id: number
  username: string
  email: string | null
  created_at: string
  roles: string[]
  permissions?: string[]
}

// module-level 持有 QueryClient 引用，在 main.ts 中注入
let _sharedQueryClient: QueryClient | null = null

/** 在 main.ts 中调用，将 QueryClient 传入 store 模块 */
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

  const isSuperAdmin = computed(() => hasRole('superadmin'))
  const isAdmin = computed(() => hasRole('admin') || isSuperAdmin.value)
  const isOperator = computed(() => hasRole('operator') || isAdmin.value)
  const canAccessBilibili = computed(
    () => hasPermission('bilibili.access') || isSuperAdmin.value,
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
    } catch (e) {
      console.error('Failed to fetch user info:', e)
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