import apiClient from './client'
import type { StatsSummaryResponse } from '../types'

export const statisticsApi = {
  getSummary: async (
    dateFrom: string,
    dateTo: string,
    excludeBudgetExcluded = false,
    userId?: number,
  ): Promise<StatsSummaryResponse> => {
    const params = new URLSearchParams({
      date_from: dateFrom,
      date_to: dateTo,
    })
    if (excludeBudgetExcluded) {
      params.set('exclude_budget_excluded', 'true')
    }
    if (userId !== undefined) {
      params.set('user_id', String(userId))
    }
    const response = await apiClient.get<StatsSummaryResponse>(
      `/statistics/summary?${params.toString()}`
    )
    return response.data
  },
}
