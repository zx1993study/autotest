export interface SystemUser {
  id: number
  username: string
  real_name: string
  phone?: string | null
  status: string
  roles: string[]
  permissions: string[]
  password_info: string
  created_at: string
  updated_at: string
  last_login_at?: number | null
}

export interface SystemUserListParams {
  keyword?: string
  status?: string
  page?: number
  pageSize?: number
}

export interface SystemUserCreatePayload {
  username: string
  real_name: string
  phone?: string | null
  password: string
  status: string
}

export interface SystemUserUpdatePayload {
  username?: string
  real_name?: string
  phone?: string | null
  status?: string
}
