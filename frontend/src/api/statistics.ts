import apiClient from './client'
import type { StatsSummaryResponse } from '../types'

export const statisticsApi = {
  getSummary: async (dateFrom: string, dateTo: string): Promise<StatsSummaryResponse> => {
    const response = await apiClient.get<StatsSummaryResponse>(
      `/statistics/summary?date_from=${dateFrom}&date_to=${dateTo}`
    )
    return response.data
  },
}
