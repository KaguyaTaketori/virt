// api/client.ts — 唯一的 axios 配置
import axios, { type AxiosInstance, type AxiosError } from 'axios'

export const apiClient: AxiosInstance = axios.create({
  baseURL: '',
  timeout: 15000,
  withCredentials: true,
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

apiClient.interceptors.response.use(
  (res) => res,
  (error: AxiosError) => {
    const status = error.response?.status
    if (status === 401) console.warn('[API] 401 未授权')
    else if (status === 403) console.error('[API] 403 权限不足')
    else if (status && status >= 500) {
      const detail = (error.response?.data as any)?.detail ?? '服务器内部错误'
      console.error(`[API] ${status}:`, detail)
    } else if (!error.response) {
      console.error('[API] 网络连接失败')
    }
    return Promise.reject(error)
  }
)