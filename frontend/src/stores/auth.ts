import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'
import router from '@/router'

interface User {
  id: number
  username: string
  email: string | null
  created_at: string
  roles: string[]
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!token.value)

  const hasRole = (role: string): boolean => {
    return user.value?.roles?.includes(role) ?? false
  }

  const isSuperAdmin = computed(() => hasRole('superadmin'))
  const isAdmin = computed(() => hasRole('admin') || isSuperAdmin.value)
  const isOperator = computed(() => hasRole('operator') || isAdmin.value)
  const canAccessBilibili = computed(() => hasRole('user') || hasRole('operator') || isAdmin.value)

  async function login(username: string, password: string) {
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

  async function register(username: string, email: string, password: string) {
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

  async function fetchUserInfo() {
    if (!token.value) return
    try {
      const res = await fetch('/api/admin/permissions/users/me', {
        headers: { Authorization: `Bearer ${token.value}` }
      })
      if (res.ok) {
        user.value = await res.json()
      }
    } catch (e) {
      console.error('Failed to fetch user info:', e)
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    router.push('/')
  }

  async function init() {
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
    login,
    register,
    logout,
    fetchUserInfo,
    init
  }
})