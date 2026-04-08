import apiClient from './client'
import type { Category } from '../types'

export const categoriesApi = {
  getAll: async (): Promise<Category[]> => {
    const response = await apiClient.get<Category[]>('/categories')
    return response.data
  },

  create: async (name: string, emoji?: string): Promise<Category> => {
    const response = await apiClient.post<Category>('/categories', { name, emoji })
    return response.data
  },

  update: async (id: number, name: string, emoji?: string, excludeFromBudget?: boolean): Promise<Category> => {
    const body: Record<string, unknown> = { name, emoji }
    if (excludeFromBudget !== undefined) body.exclude_from_budget = excludeFromBudget
    const response = await apiClient.put<Category>(`/categories/${id}`, body)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/categories/${id}`)
  },

  toggleBudgetExclusion: async (id: number): Promise<Category> => {
    const response = await apiClient.post<Category>(`/categories/${id}/toggle-budget-exclusion`)
    return response.data
  },
}
