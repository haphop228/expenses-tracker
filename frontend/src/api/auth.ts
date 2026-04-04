import apiClient from './client'
import type {
  TokenResponse,
  AccessTokenResponse,
  User,
  LinkCodeResponse,
} from '../types'

export const authApi = {
  login: async (username: string, password: string): Promise<TokenResponse> => {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    const response = await apiClient.post<TokenResponse>('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return response.data
  },

  register: async (
    inviteCode: string,
    username: string,
    password: string,
    displayName?: string
  ): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>(
      `/auth/register/${inviteCode}`,
      { username, password, display_name: displayName }
    )
    return response.data
  },

  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout')
  },

  refresh: async (refreshToken: string): Promise<AccessTokenResponse> => {
    const response = await apiClient.post<AccessTokenResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    })
    return response.data
  },

  me: async (): Promise<User> => {
    const response = await apiClient.get<User>('/auth/me')
    return response.data
  },

  generateLinkCode: async (): Promise<LinkCodeResponse> => {
    const response = await apiClient.post<LinkCodeResponse>('/auth/generate-link-code')
    return response.data
  },
}
