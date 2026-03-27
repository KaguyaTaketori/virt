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
}

export const channelApi = {
  getAll: (params?: Record<string, any>) => api.get('/api/channels', { params }),
  get: (id: number) => api.get(`/api/channels/${id}`),
  create: (data: Partial<Channel>) => api.post('/api/channels', data),
  update: (id: number, data: Partial<Channel>) => api.put(`/api/channels/${id}`, data),
  delete: (id: number) => api.delete(`/api/channels/${id}`),
}

export default api
