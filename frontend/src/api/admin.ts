import axios from 'axios'
import type { AdminTokenResponse, AdminGroupResponse, AdminGroupDetail } from '../types/admin'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

// Отдельный клиент для admin (без user JWT)
const adminClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

adminClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const adminApi = {
  login: async (login: string, password: string, totpCode?: string): Promise<AdminTokenResponse> => {
    const response = await adminClient.post<AdminTokenResponse>('/admin/login', {
      login,
      password,
      totp_code: totpCode,
    })
    return response.data
  },

  getGroups: async (page = 1, perPage = 20): Promise<{ items: AdminGroupResponse[]; total: number }> => {
    const response = await adminClient.get<AdminGroupResponse[]>(`/admin/groups?page=${page}&per_page=${perPage}`)
    const items = response.data
    return { items, total: items.length }
  },

  getGroup: async (groupId: number): Promise<AdminGroupDetail> => {
    const response = await adminClient.get<AdminGroupDetail>(`/admin/groups/${groupId}`)
    return response.data
  },

  createGroup: async (name: string): Promise<AdminGroupDetail> => {
    const response = await adminClient.post<AdminGroupDetail>('/admin/groups', { name })
    return response.data
  },

  toggleGroup: async (groupId: number, isActive: boolean): Promise<AdminGroupResponse> => {
    const response = await adminClient.patch<AdminGroupResponse>(`/admin/groups/${groupId}`, {
      is_active: isActive,
    })
    return response.data
  },

  deleteGroup: async (groupId: number): Promise<void> => {
    await adminClient.delete(`/admin/groups/${groupId}`)
  },

  getUsers: async (groupId: number): Promise<unknown[]> => {
    const response = await adminClient.get(`/admin/groups/${groupId}/users`)
    return response.data
  },

  generateInvite: async (groupId: number): Promise<{ code: string; expires_at: string; group_id: number }> => {
    const response = await adminClient.post(`/admin/groups/${groupId}/invite`)
    return response.data
  },
}
