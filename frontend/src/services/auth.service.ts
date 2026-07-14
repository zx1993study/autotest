import { request } from '../api/client'
import type { AuthUser, BootstrapAuthInfo, LoginPayload, LoginResult } from '../types/auth'

export function login(payload: LoginPayload) {
  return request<LoginResult>({ method: 'POST', url: '/auth/login', data: payload })
}

export function getCurrentUser() {
  return request<AuthUser>({ method: 'GET', url: '/auth/me' })
}

export function logout() {
  return request<{ logged_out: boolean }>({ method: 'POST', url: '/auth/logout', data: {} })
}

export function getAuthBootstrap() {
  return request<BootstrapAuthInfo>({ method: 'GET', url: '/auth/bootstrap' })
}
