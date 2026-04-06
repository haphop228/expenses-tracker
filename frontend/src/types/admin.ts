export interface AdminTokenResponse {
  access_token: string
  token_type: string
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
  username: string
  display_name: string | null
  is_admin: boolean
  telegram_id: number | null
  created_at: string
}

export interface AdminGroupDetail {
  id: number
  name: string
  max_members: number
  created_at: string
  members: AdminGroupMember[]
  statistics: Record<string, unknown>
}
