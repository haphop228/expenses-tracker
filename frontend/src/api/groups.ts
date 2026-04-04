import apiClient from './client'
import type { Group, GroupSettings, Member, InviteResponse } from '../types'

export const groupsApi = {
  getInfo: async (): Promise<Group> => {
    const response = await apiClient.get<Group>('/groups/me')
    return response.data
  },

  getMembers: async (): Promise<Member[]> => {
    const response = await apiClient.get<Member[]>('/groups/members')
    return response.data
  },

  getSettings: async (): Promise<GroupSettings> => {
    const response = await apiClient.get<GroupSettings>('/groups/settings')
    return response.data
  },

  updateSettings: async (settings: Partial<GroupSettings>): Promise<GroupSettings> => {
    const response = await apiClient.patch<GroupSettings>('/groups/settings', settings)
    return response.data
  },

  generateInvite: async (): Promise<InviteResponse> => {
    const response = await apiClient.post<InviteResponse>('/groups/invite')
    return response.data
  },

  removeMember: async (userId: number): Promise<void> => {
    await apiClient.delete(`/groups/members/${userId}`)
  },

  updateMemberRole: async (userId: number, isAdmin: boolean): Promise<Member> => {
    const response = await apiClient.patch<Member>(`/groups/members/${userId}`, { is_admin: isAdmin })
    return response.data
  },
}
