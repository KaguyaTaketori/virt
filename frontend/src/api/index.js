import axios from 'axios'

const api = axios.create({
  baseURL: '',
  timeout: 10000
})

export const streamApi = {
  getLiveStreams: () => api.get('/api/streams/live'),
  getAllStreams: (params) => api.get('/api/streams', { params })
}

export default api