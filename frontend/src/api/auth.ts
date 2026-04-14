import { apiClient } from './client'

export const authApi = {
  login: (username: string, password: string) =>
    apiClient.post(
      '/api/auth/login',
      new URLSearchParams({ username, password }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    ),
  logout: () =>
    apiClient.post('/api/auth/logout'),
  register: (data: { username: string; email?: string; password: string }) =>
    apiClient.post('/api/auth/register', data),
  getUserInfo: () =>
    apiClient.get('/api/admin/permissions/users/me'),
}