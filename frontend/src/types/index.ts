// Auth types
export interface User {
  id: number
  group_id: number | null
  name: string
  web_login: string | null
  telegram_id: number | null
  telegram_username: string | null
  role: string
  reminder_enabled: boolean
  created_at: string
  last_seen: string | null
  group_name?: string | null
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

// Group types
export interface Group {
  id: number
  name: string
  max_members: number
  created_at: string
  current_members: number
  settings: GroupSettings | null
}

export interface GroupSettings {
  reminder_time: string
  timezone: string
  currency: string
}

export interface Member {
  id: number
  name: string
  web_login: string | null
  telegram_id: number | null
  telegram_username: string | null
  role: string
  reminder_enabled: boolean
  created_at: string
  last_seen: string | null
}

// Category types
export interface Category {
  id: number
  name: string
  emoji: string | null
  exclude_from_budget: boolean
  created_at: string
}

// Expense types
export interface Expense {
  id: number
  user_id: number | null
  user_name: string | null
  category_id: number | null
  category_name: string | null
  category_emoji: string | null
  amount: number
  comment: string | null
  created_at: string
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
  category_id: number | null
  category_name: string | null
  category_emoji: string | null
  total: number
  count: number
  percentage: number
}

export interface UserStats {
  user_id: number
  user_name: string
  total: number
  count: number
  percentage: number
}

export interface StatsSummaryResponse {
  total_amount: number
  total_count: number
  average_per_day: number
  by_category: CategoryStats[]
  by_user: UserStats[]
}

// Budget types
export interface BudgetCategoryItem {
  category_id: number
  category_name: string
  category_emoji: string | null
  budget: number | null
  spent: number
  remaining: number | null
  percentage_used: number | null
}

export interface BudgetResponse {
  month: string
  total_budget: number | null
  total_spent: number
  remaining: number | null
  percentage_used: number | null
  days_remaining: number
  daily_budget_remaining: number | null
  forecast: number | null
  forecast_over_budget: number | null
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
  code: string
  url: string
  expires_at: string
}

export interface LinkCodeResponse {
  link_code: string
  expires_at: string
  command: string
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
