import apiClient from './client'
import type {
  Expense,
  PaginatedExpenses,
  ExpenseCreate,
  ExpenseUpdate,
  ExpenseFilters,
} from '../types'

export const expensesApi = {
  getAll: async (filters: ExpenseFilters = {}): Promise<PaginatedExpenses> => {
    const params = new URLSearchParams()
    if (filters.page) params.append('page', String(filters.page))
    if (filters.per_page) params.append('per_page', String(filters.per_page))
    if (filters.category_id) params.append('category_id', String(filters.category_id))
    if (filters.date_from) params.append('date_from', filters.date_from)
    if (filters.date_to) params.append('date_to', filters.date_to)
    if (filters.user_id) params.append('user_id', String(filters.user_id))
    const response = await apiClient.get<PaginatedExpenses>(`/expenses?${params}`)
    return response.data
  },

  getById: async (id: number): Promise<Expense> => {
    const response = await apiClient.get<Expense>(`/expenses/${id}`)
    return response.data
  },

  create: async (data: ExpenseCreate): Promise<Expense> => {
    const response = await apiClient.post<Expense>('/expenses', data)
    return response.data
  },

  update: async (id: number, data: ExpenseUpdate): Promise<Expense> => {
    const response = await apiClient.patch<Expense>(`/expenses/${id}`, data)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/expenses/${id}`)
  },
}
