export interface AuthUser {
  id: number
  username: string
  display_name: string
  roles: string[]
  permissions: string[]
}

export interface LoginPayload {
  username: string
  password: string
}

export interface LoginResult {
  access_token: string
  token_type: string
  expires_in: number
  user: AuthUser
}

export interface BootstrapAuthInfo {
  default_username: string
  password_policy: string
}
