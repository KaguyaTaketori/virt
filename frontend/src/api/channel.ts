import { apiClient } from './client'
import type { Channel, PaginatedVideos, BilibiliInfo, BilibiliInfoData, BilibiliVideosData, BilibiliDynamicsData } from '@/types'

export const channelApi = {
  getAll:    (params?: Record<string, unknown>) =>
    apiClient.get<Channel[]>('/api/channels/', { params }),

  get:       (id: string) =>
    apiClient.get<Channel>(`/api/channels/${id}`),

  getBilibili: (id: string, dynamicsOffset?: string, dynamicsLimit?: number) =>
    apiClient.get<BilibiliInfo>(`/api/channels/${id}/bilibili`, {
      params: { dynamics_offset: dynamicsOffset, dynamics_limit: dynamicsLimit },
    }),

  getBilibiliInfo: (id: string) =>
    apiClient.get<BilibiliInfoData>(`/api/channels/${id}/bilibili/info`),

  getBilibiliVideos: (id: string, page?: number, pageSize?: number) =>
    apiClient.get<BilibiliVideosData>(`/api/channels/${id}/bilibili/videos`, {
      params: { page, page_size: pageSize },
    }),

  getBilibiliDynamics: (id: string, offset?: string, limit?: number) =>
    apiClient.get<BilibiliDynamicsData>(`/api/channels/${id}/bilibili/dynamics`, {
      params: { offset, limit },
    }),

  getVideos: (id: string, page?: number, pageSize?: number, status?: string) =>
    apiClient.get<PaginatedVideos>(`/api/channels/${id}/videos`, {
      params: { page, page_size: pageSize, status },
    }),

  create:    (data: Partial<Channel>) =>
    apiClient.post<Channel>('/api/channels/', data),

  update:    (id: string, data: Partial<Channel>) =>
    apiClient.put<Channel>(`/api/channels/${id}`, data),

  delete:    (id: string) =>
    apiClient.delete(`/api/channels/${id}`),
}
