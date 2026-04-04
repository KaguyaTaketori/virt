// frontend/src/stores/auth.ts  ← 完整替换原文件
// ─────────────────────────────────────────────────────────────────────────────
// 修复内容：
//   [低] 注销后 TanStack Query 缓存残留（前一用户数据对新用户短暂可见）
//     → logout 时调用 queryClient.clear() 清空所有缓存
//   [低] 前端权限判断逻辑重复（canAccessBilibili 散落在多个视图）
//     → 权限逻辑已保留在此 store，使用说明见 useBilibiliGuard composable
// ─────────────────────────────────────────────────────────────────────────────

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'
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

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(null)
  const loading = ref(false)

  // 获取 QueryClient 用于注销时清空缓存
  // 注意：需要在 Pinia 外部（组件内）通过 useQueryClient() 获取
  // 此处使用懒加载模式避免在 store 初始化时报错
  let _queryClient: ReturnType<typeof useQueryClient> | null = null

  function _getQueryClient() {
    if (!_queryClient) {
      try {
        _queryClient = useQueryClient()
      } catch {
        // store 在组件外使用时 useQueryClient 可能失败，忽略
      }
    }
    return _queryClient
  }

  const isLoggedIn = computed(() => !!token.value)

  const hasRole = (role: string): boolean =>
    user.value?.roles?.includes(role) ?? false

  const hasPermission = (perm: string): boolean =>
    user.value?.permissions?.includes(perm) ?? false

  const isSuperAdmin = computed(() => hasRole('superadmin'))
  const isAdmin = computed(() => hasRole('admin') || isSuperAdmin.value)
  const isOperator = computed(() => hasRole('operator') || isAdmin.value)

  const canAccessBilibili = computed(
    () => hasPermission('bilibili.access') || isSuperAdmin.value
  )

  async function login(username: string, password: string): Promise<boolean> {
    loading.value = true
    try {
      const res = await authApi.login(username, password)
      token.value = res.data.access_token
      localStorage.setItem('token', res.data.access_token)
      await fetchUserInfo()
      return true
    } catch (e) {
      console.error('Login failed:', e)
      return false
    } finally {
      loading.value = false
    }
  }

  async function register(
    username: string,
    email: string,
    password: string
  ): Promise<boolean> {
    loading.value = true
    try {
      await authApi.register({ username, email, password })
      return await login(username, password)
    } catch (e) {
      console.error('Register failed:', e)
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

    const qc = _getQueryClient()
    if (qc) {
      qc.clear()
    }

    token.value = null
    user.value = null
    localStorage.removeItem('token')

    router.push('/')
  }

  async function init(): Promise<void> {
    if (token.value) {
      await fetchUserInfo()
    }
  }

  return {
    token,
    user,
    loading,
    isLoggedIn,
    isSuperAdmin,
    isAdmin,
    isOperator,
    canAccessBilibili,
    hasRole,
    hasPermission,
    login,
    register,
    logout,
    fetchUserInfo,
    init,
  }
})