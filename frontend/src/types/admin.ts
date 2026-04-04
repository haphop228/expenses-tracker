export interface AdminTokenResponse {
  access_token: string
  token_type: string
}

export interface AdminGroupResponse {
  id: number
  name: string
  slug: string
  is_active: boolean
  members_count: number
  expenses_count: number
  created_at: string
}

export interface AdminGroupDetail extends AdminGroupResponse {
  settings: {
    timezone: string
    currency: string
    reminder_enabled: boolean
    reminder_time: string | null
  }
  members: Array<{
    id: number
    username: string
    display_name: string | null
    is_admin: boolean
    telegram_id: number | null
    created_at: string
  }>
}
