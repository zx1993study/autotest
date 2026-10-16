import { request } from '../api/client'
import type { PageResult } from '../types/api'
import type {
  SystemUser,
  SystemUserCreatePayload,
  SystemUserListParams,
  SystemUserUpdatePayload
} from '../types/system-user'

const SYSTEM_USER_PATH = '/system/users'

export function listSystemUsers(params: SystemUserListParams, signal?: AbortSignal) {
  return request<PageResult<SystemUser>>({ method: 'GET', url: SYSTEM_USER_PATH, params, signal })
}

export function createSystemUser(payload: SystemUserCreatePayload) {
  return request<SystemUser>({ method: 'POST', url: SYSTEM_USER_PATH, data: payload })
}

export function updateSystemUser(userId: number, payload: SystemUserUpdatePayload) {
  return request<SystemUser>({ method: 'PUT', url: `${SYSTEM_USER_PATH}/${userId}`, data: payload })
}

export function deleteSystemUser(userId: number) {
  return request<boolean>({ method: 'DELETE', url: `${SYSTEM_USER_PATH}/${userId}` })
}

export function resetSystemUserPassword(userId: number, password: string) {
  return request<SystemUser>({
    method: 'POST',
    url: `${SYSTEM_USER_PATH}/${userId}/reset-password`,
    data: { password }
  })
}
