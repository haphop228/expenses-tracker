import apiClient from './client'
import type { StatsSummaryResponse } from '../types'

export const statisticsApi = {
  getSummary: async (
    dateFrom: string,
    dateTo: string,
    excludeBudgetExcluded = false,
  ): Promise<StatsSummaryResponse> => {
    const params = new URLSearchParams({
      date_from: dateFrom,
      date_to: dateTo,
    })
    if (excludeBudgetExcluded) {
      params.set('exclude_budget_excluded', 'true')
    }
    const response = await apiClient.get<StatsSummaryResponse>(
      `/statistics/summary?${params.toString()}`
    )
    return response.data
  },
}
