import { computed, readonly, ref } from 'vue'

import { getCurrentUser, login as loginRequest, logout as logoutRequest } from '../services/auth.service'
import { clearRemoteOptionsCache } from '../services/resource.service'
import type { AuthUser, LoginPayload } from '../types/auth'
import { readSessionValue, removeSessionValue, writeSessionValue } from '../utils/browserSession'

const ACCESS_TOKEN_KEY = 'access_token'
const CURRENT_USER_KEY = 'current_user'

const token = ref(readSessionValue(ACCESS_TOKEN_KEY))
const currentUser = ref<AuthUser | null>(readCurrentUser())
const initialized = ref(false)

async function login(payload: LoginPayload) {
  const result = await loginRequest(payload)
  if (!result || typeof result.access_token !== 'string' || !result.access_token || !isAuthUser(result.user)) throw new Error('登录接口返回数据不完整，请重试。')
  setSession(result.access_token, result.user)
  return result.user
}

async function loadCurrentUser() {
  if (!token.value) {
    initialized.value = true
    return null
  }
  try {
    const user = await getCurrentUser()
    setSession(token.value, user)
    return user
  } catch {
    clearSession()
    return null
  } finally {
    initialized.value = true
  }
}

async function logout() {
  if (token.value) {
    try {
      await logoutRequest()
    } catch {
      // Logout must always clear the browser session even if the server token has expired.
    }
  }
  clearSession()
}

function setSession(accessToken: string, user: AuthUser) {
  if (token.value !== accessToken) clearRemoteOptionsCache()
  token.value = accessToken
  currentUser.value = user
  writeSessionValue(ACCESS_TOKEN_KEY, accessToken)
  writeSessionValue(CURRENT_USER_KEY, JSON.stringify(user))
}

function clearSession() {
  clearRemoteOptionsCache()
  token.value = ''
  currentUser.value = null
  removeSessionValue(ACCESS_TOKEN_KEY)
  removeSessionValue(CURRENT_USER_KEY)
}

function readCurrentUser(): AuthUser | null {
  const raw = readSessionValue(CURRENT_USER_KEY)
  if (!raw) {
    return null
  }
  try {
    const user = JSON.parse(raw)
    return isAuthUser(user) ? user : null
  } catch {
    return null
  }
}

function isAuthUser(value: unknown): value is AuthUser {
  return typeof value === 'object' && value !== null && 'id' in value && 'username' in value
}

export function useAuthStore() {
  return {
    token: readonly(token),
    currentUser: readonly(currentUser),
    initialized: readonly(initialized),
    isAuthenticated: computed(() => Boolean(token.value && currentUser.value)),
    login,
    loadCurrentUser,
    logout,
    clearSession
  }
}
