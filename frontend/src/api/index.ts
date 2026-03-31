import axios from 'axios'
import type { AxiosInstance } from 'axios'

const api: AxiosInstance = axios.create({
  baseURL: '',
  timeout: 10000
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const streamApi = {
  getLiveStreams: () => api.get('/api/streams/live'),
  getAllStreams: (params?: Record<string, any>) => api.get('/api/streams', { params })
}

export interface Channel {
  id: number
  platform: 'youtube' | 'bilibili'
  channel_id: string
  name: string
  avatar_url: string | null
  is_active: boolean
  org_id: number | null
  avatar_shape: 'circle' | 'square'
  banner_url: string | null
  twitter_url: string | null
  youtube_url: string | null
  description: string | null
  is_liked: boolean
  is_blocked: boolean
  bilibili_sign: string | null
  bilibili_fans: number | null
  bilibili_archive_count: number | null
}

export interface Organization {
  id: number
  name: string
  name_en: string | null
  logo_url: string | null
  website: string | null
  logo_shape: 'circle' | 'square'
}

export interface Video {
  id: string
  title: string
  thumbnail_url: string | null
  duration: string | null
  view_count: number
  published_at: string | null
  status: string
}

export interface PaginatedVideos {
  videos: Video[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export const channelApi = {
  getAll: (params?: Record<string, any>) => api.get('/api/channels', { params }),
  get: (id: number) => api.get(`/api/channels/${id}`),
  getVideos: (id: number, page?: number, pageSize?: number, status?: string) => 
    api.get(`/api/channels/${id}/videos`, { params: { page, page_size: pageSize, status } }),
  create: (data: Partial<Channel>) => api.post('/api/channels', data),
  update: (id: number, data: Partial<Channel>) => api.put(`/api/channels/${id}`, data),
  delete: (id: number) => api.delete(`/api/channels/${id}`),
}

export const authApi = {
  login: (username: string, password: string) => 
    api.post('/api/auth/login', new URLSearchParams({ username, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    }),
  register: (data: { username: string; email?: string; password: string }) => 
    api.post('/api/auth/register', data),
}

export const userChannelApi = {
  like: (channelId: number) => api.post(`/api/users/channels/${channelId}/like`),
  unlike: (channelId: number) => api.delete(`/api/users/channels/${channelId}/like`),
  block: (channelId: number) => api.post(`/api/users/channels/${channelId}/block`),
  unblock: (channelId: number) => api.delete(`/api/users/channels/${channelId}/block`),
  getLiked: () => api.get('/api/users/channels', { params: { type: 'liked' } }),
  getBlocked: () => api.get('/api/users/channels', { params: { type: 'blocked' } }),
}

export const orgApi = {
  getAll: () => api.get('/api/organizations'),
  get: (id: number) => api.get(`/api/organizations/${id}`),
  create: (data: Partial<Organization>) => api.post('/api/organizations', data),
  update: (id: number, data: Partial<Organization>) => api.put(`/api/organizations/${id}`, data),
  delete: (id: number) => api.delete(`/api/organizations/${id}`),
}

export const adminVideosApi = {
  getVideos: (params: {
    channel_id: number
    status?: string | null
    duration_min?: number | null
    duration_max?: number | null
    page?: number
    page_size?: number
  }) =>
    api.get('/api/admin/videos', {
      params: {
        channel_id: params.channel_id,
        status: params.status ?? undefined,
        duration_min: params.duration_min ?? undefined,
        duration_max: params.duration_max ?? undefined,
        page: params.page ?? undefined,
        page_size: params.page_size ?? undefined,
      },
    }),
  batchUpdateStatus: (payload: { video_ids: string[]; new_status: string }) =>
    api.post('/api/admin/videos/batch-update-status', payload),
}

export default api
