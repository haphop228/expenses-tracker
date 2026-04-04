// Auth types
export interface User {
  id: number
  username: string
  display_name: string | null
  telegram_id: number | null
  is_admin: boolean
  is_active: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

export interface AccessTokenResponse {
  access_token: string
  token_type: string
}

export interface LinkCodeResponse {
  link_code: string
  expires_in: number
}

// Group types
export interface Group {
  id: number
  name: string
  slug: string
  is_active: boolean
  created_at: string
}

export interface GroupSettings {
  timezone: string
  currency: string
  reminder_enabled: boolean
  reminder_time: string | null
  budget_warning_threshold: number
}

export interface Member {
  id: number
  username: string
  display_name: string | null
  telegram_id: number | null
  is_admin: boolean
  is_active: boolean
  joined_at: string
}

// Category types
export interface Category {
  id: number
  name: string
  emoji: string | null
  is_active: boolean
  exclude_from_budget: boolean
}

// Expense types
export interface ExpenseUserInfo {
  id: number
  username: string
  display_name: string | null
}

export interface ExpenseCategoryInfo {
  id: number
  name: string
  emoji: string | null
}

export interface Expense {
  id: number
  amount: number
  comment: string | null
  created_at: string
  user: ExpenseUserInfo
  category: ExpenseCategoryInfo
}

export interface PaginatedExpenses {
  items: Expense[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface ExpenseCreate {
  category_id: number
  amount: number
  comment?: string
  created_at?: string
}

export interface ExpenseUpdate {
  amount?: number
  comment?: string
  category_id?: number
}

// Statistics types
export interface CategoryStats {
  category_id: number
  category_name: string
  emoji: string | null
  total: number
  count: number
  percentage: number
}

export interface UserStats {
  user_id: number
  username: string
  display_name: string | null
  total: number
  count: number
  percentage: number
}

export interface StatsSummaryResponse {
  date_from: string
  date_to: string
  total: number
  by_category: CategoryStats[]
  by_user: UserStats[]
}

// Budget types
export interface BudgetCategoryItem {
  category_id: number
  category_name: string
  emoji: string | null
  budget_limit: number | null
  spent: number
  percentage: number | null
  exclude_from_budget: boolean
}

export interface BudgetResponse {
  month: string
  budget_limit: number | null
  total_spent: number
  remaining: number | null
  percentage: number | null
  by_category: BudgetCategoryItem[]
}

export interface BudgetSet {
  amount: number
}

export interface BudgetCategorySet {
  category_id: number
  amount: number
}

// Invite types
export interface InviteResponse {
  invite_code: string
  expires_at: string
}

// API error
export interface ApiError {
  detail: string
}

// Filters
export interface ExpenseFilters {
  page?: number
  per_page?: number
  category_id?: number
  date_from?: string
  date_to?: string
  user_id?: number
}
