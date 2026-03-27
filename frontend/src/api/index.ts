import axios from 'axios'
import type { AxiosInstance } from 'axios'

const api: AxiosInstance = axios.create({
  baseURL: '',
  timeout: 10000
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
}

export interface Organization {
  id: number
  name: string
  name_en: string | null
  logo_url: string | null
  website: string | null
  logo_shape: 'circle' | 'square'
}

export const channelApi = {
  getAll: (params?: Record<string, any>) => api.get('/api/channels', { params }),
  get: (id: number) => api.get(`/api/channels/${id}`),
  create: (data: Partial<Channel>) => api.post('/api/channels', data),
  update: (id: number, data: Partial<Channel>) => api.put(`/api/channels/${id}`, data),
  delete: (id: number) => api.delete(`/api/channels/${id}`),
}

export const orgApi = {
  getAll: () => api.get('/api/organizations'),
  get: (id: number) => api.get(`/api/organizations/${id}`),
  create: (data: Partial<Organization>) => api.post('/api/organizations', data),
  update: (id: number, data: Partial<Organization>) => api.put(`/api/organizations/${id}`, data),
  delete: (id: number) => api.delete(`/api/organizations/${id}`),
}

export default api
