import { apiClient } from "./client"
import type { PaginatedVideos, Role, Permission, UserWithRoles } from '@/types'


export const adminVideosApi = {
  getVideos: (params: {
    channel_id: string
    status?: string | null
    duration_min?: number | null
    duration_max?: number | null
    page?: number
    page_size?: number
  }) =>
    apiClient.get<PaginatedVideos>('/api/admin/videos', {
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
    apiClient.post('/api/admin/videos/batch-update-status', payload),
}

export const adminPermissionsApi = {
  getRoles: () => apiClient.get<Role[]>('/api/admin/permissions/roles'),
  createRole: (data: { name: string; description?: string }) =>
    apiClient.post<Role>('/api/admin/permissions/roles', data),
  getRolePermissions: (roleId: number) =>
    apiClient.get<number[]>(`/api/admin/permissions/roles/${roleId}/permissions`),
  getPermissions: () => apiClient.get<Permission[]>('/api/admin/permissions/permissions'),
  createPermission: (data: { name: string; description?: string; resource: string; action: string }) =>
    apiClient.post<Permission>('/api/admin/permissions/permissions', data),
  assignPermissionsToRole: (roleId: number, permissionIds: number[]) =>
    apiClient.post(`/api/admin/permissions/roles/${roleId}/permissions`, permissionIds),
  getUsers: (skip = 0, limit = 100) =>
    apiClient.get<UserWithRoles[]>('/api/admin/permissions/users', { params: { skip, limit } }),
  getUser: (userId: number) =>
    apiClient.get<UserWithRoles>(`/api/admin/permissions/users/${userId}`),
  updateUserRoles: (userId: number, roleIds: number[]) =>
    apiClient.put(`/api/admin/permissions/users/${userId}/roles`, { role_ids: roleIds }),
  createResourceACL: (userId: number, resource: string, resourceId: number, access: string) =>
    apiClient.post(`/api/admin/permissions/users/${userId}/resource-acl`, null, { params: { resource, resource_id: resourceId, access } }),
  deleteResourceACL: (aclId: number) =>
    apiClient.delete(`/api/admin/permissions/resource-acl/${aclId}`),
}