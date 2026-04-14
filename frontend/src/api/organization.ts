import { apiClient } from './client'
import type { Organization } from '@/types'


export const orgApi = {
  getAll:  () =>
    apiClient.get<Organization[]>('/api/organizations'),

  get:     (id: number) =>
    apiClient.get<Organization>(`/api/organizations/${id}`),

  create:  (data: Partial<Organization>) =>
    apiClient.post<Organization>('/api/organizations', data),

  update:  (id: number, data: Partial<Organization>) =>
    apiClient.put<Organization>(`/api/organizations/${id}`, data),

  delete:  (id: number) =>
    apiClient.delete(`/api/organizations/${id}`),
}