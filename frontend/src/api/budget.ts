import apiClient from './client'
import type { BudgetResponse } from '../types'

export const budgetApi = {
  get: async (month: string): Promise<BudgetResponse> => {
    const response = await apiClient.get<BudgetResponse>(`/budget?month=${month}`)
    return response.data
  },

  set: async (month: string, amount: number): Promise<BudgetResponse> => {
    const response = await apiClient.post<BudgetResponse>('/budget/set', { month, amount })
    return response.data
  },

  setCategoryLimit: async (
    month: string,
    categoryId: number,
    amount: number
  ): Promise<void> => {
    await apiClient.post('/budget/set-category', {
      month,
      category_id: categoryId,
      amount,
    })
  },
}
