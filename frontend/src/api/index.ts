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

export default api
