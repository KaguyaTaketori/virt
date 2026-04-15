// frontend/src/api/index.ts
import axios from 'axios'
import type { AxiosInstance, AxiosError } from 'axios'
import type { Stream, Channel, Organization, Video, PaginatedVideos, ContentNode, BilibiliInfo, BilibiliInfoData, BilibiliVideosData, BilibiliDynamicsData, Role, Permission, UserWithRoles } from '@/types'

const api: AxiosInstance = axios.create({
  baseURL: '',
  timeout: 15000,
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})


api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const status = error.response?.status

    if (status === 401) {
      console.warn('[API] 401 未授权')
    } else if (status === 403) {
      console.error('[API] 403 权限不足')
    } else if (status && status >= 500) {
      const detail = (error.response?.data as any)?.detail ?? '服务器内部错误'
      console.error(`[API] ${status} 服务器错误:`, detail)
    } else if (!error.response) {
      console.error('[API] 网络连接失败，请检查网络或稍后重试')
    }

    return Promise.reject(error)
  }
)

export type { Stream, Channel, Organization, Video, PaginatedVideos, ContentNode, BilibiliInfo, Role, Permission, UserWithRoles }

// ── API 方法 ──────────────────────────────────────────────────────────────────

export const streamApi = {
  getLiveStreams: () => api.get<Stream[]>('/api/streams/live'),
  getAllStreams:   (params?: Record<string, unknown>) =>
    api.get<Stream[]>('/api/streams', { params }),
}

export const channelApi = {
  getAll:    (params?: Record<string, unknown>) =>
    api.get<Channel[]>('/api/channels/', { params }),

  get:       (id: string) =>
    api.get<Channel>(`/api/channels/${id}`),

  getBilibili: (id: string, dynamicsOffset?: string, dynamicsLimit?: number) =>
    api.get<BilibiliInfo>(`/api/channels/${id}/bilibili`, {
      params: { dynamics_offset: dynamicsOffset, dynamics_limit: dynamicsLimit },
    }),

  getBilibiliInfo: (id: string) =>
    api.get<BilibiliInfoData>(`/api/channels/${id}/bilibili/info`),

  getBilibiliVideos: (id: string, page?: number, pageSize?: number) =>
    api.get<BilibiliVideosData>(`/api/channels/${id}/bilibili/videos`, {
      params: { page, page_size: pageSize },
    }),

  getBilibiliDynamics: (id: string, offset?: string, limit?: number) =>
    api.get<BilibiliDynamicsData>(`/api/channels/${id}/bilibili/dynamics`, {
      params: { offset, limit },
    }),

  getVideos: (id: string, page?: number, pageSize?: number, status?: string) =>
    api.get<PaginatedVideos>(`/api/channels/${id}/videos`, {
      params: { page, page_size: pageSize, status },
    }),

  create:    (data: Partial<Channel>) =>
    api.post<Channel>('/api/channels/', data),

  update:    (id: string, data: Partial<Channel>) =>
    api.put<Channel>(`/api/channels/${id}`, data),

  delete:    (id: string) =>
    api.delete(`/api/channels/${id}`),
}

export const orgApi = {
  getAll:  () =>
    api.get<Organization[]>('/api/organizations'),

  get:     (id: number) =>
    api.get<Organization>(`/api/organizations/${id}`),

  create:  (data: Partial<Organization>) =>
    api.post<Organization>('/api/organizations', data),

  update:  (id: number, data: Partial<Organization>) =>
    api.put<Organization>(`/api/organizations/${id}`, data),

  delete:  (id: number) =>
    api.delete(`/api/organizations/${id}`),
}

export const authApi = {
  login: (username: string, password: string) =>
    api.post(
      '/api/auth/login',
      new URLSearchParams({ username, password }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    ),
  logout: () =>
    api.post('/api/auth/logout'),
  register: (data: { username: string; email?: string; password: string }) =>
    api.post('/api/auth/register', data),
  getUserInfo: () =>
    api.get('/api/admin/permissions/users/me'),
}

export const userChannelApi = {
  like:       (channelId: number) =>
    api.post(`/api/users/channels/${channelId}/like`),
  unlike:     (channelId: number) =>
    api.delete(`/api/users/channels/${channelId}/like`),
  block:      (channelId: number) =>
    api.post(`/api/users/channels/${channelId}/block`),
  unblock:    (channelId: number) =>
    api.delete(`/api/users/channels/${channelId}/block`),
  getLiked:   () =>
    api.get<Channel[]>('/api/users/channels', { params: { type: 'liked' } }),
  getBlocked: () =>
    api.get<Channel[]>('/api/users/channels', { params: { type: 'blocked' } }),
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
    api.get<PaginatedVideos>('/api/admin/videos', {
      params: {
        channel_id:   params.channel_id,
        status:       params.status       ?? undefined,
        duration_min: params.duration_min ?? undefined,
        duration_max: params.duration_max ?? undefined,
        page:         params.page         ?? undefined,
        page_size:    params.page_size    ?? undefined,
      },
    }),

  batchUpdateStatus: (payload: { video_ids: string[]; new_status: string }) =>
    api.post('/api/admin/videos/batch-update-status', payload),
}

export const adminPermissionsApi = {
  getRoles: () => api.get<Role[]>('/api/admin/permissions/roles'),
  createRole: (data: { name: string; description?: string }) =>
    api.post<Role>('/api/admin/permissions/roles', data),
  getRolePermissions: (roleId: number) =>
    api.get<number[]>(`/api/admin/permissions/roles/${roleId}/permissions`),
  getPermissions: () => api.get<Permission[]>('/api/admin/permissions/permissions'),
  createPermission: (data: { name: string; description?: string; resource: string; action: string }) =>
    api.post<Permission>('/api/admin/permissions/permissions', data),
  assignPermissionsToRole: (roleId: number, permissionIds: number[]) =>
    api.post(`/api/admin/permissions/roles/${roleId}/permissions`, permissionIds),
  getUsers: (skip = 0, limit = 100) =>
    api.get<UserWithRoles[]>('/api/admin/permissions/users', { params: { skip, limit } }),
  getUser: (userId: number) =>
    api.get<UserWithRoles>(`/api/admin/permissions/users/${userId}`),
  updateUserRoles: (userId: number, roleIds: number[]) =>
    api.put(`/api/admin/permissions/users/${userId}/roles`, { role_ids: roleIds }),
  createResourceACL: (userId: number, resource: string, resourceId: number, access: string) =>
    api.post(`/api/admin/permissions/users/${userId}/resource-acl`, null, { params: { resource, resource_id: resourceId, access } }),
  deleteResourceACL: (aclId: number) =>
    api.delete(`/api/admin/permissions/resource-acl/${aclId}`),
}

export default api