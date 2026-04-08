export interface AdminTokenResponse {
  access_token: string
  token_type: string
  admin: Record<string, unknown>
}

export interface AdminGroupResponse {
  id: number
  name: string
  members_count: number
  expenses_count: number
  total_spent_month: number
  last_activity: string | null
  created_at: string
}

export interface AdminGroupMember {
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

export interface AdminGroupStatistics {
  total_expenses: number
  month_spent: number
  members_count: number
}

export interface AdminGroupDetail {
  id: number
  name: string
  max_members: number
  created_at: string
  members: AdminGroupMember[]
  statistics: AdminGroupStatistics
}
