import axios from 'axios'
import type { AxiosError, AxiosRequestConfig } from 'axios'

import { requestStore } from '../store/request'
import type { ApiResult } from '../types/api'

export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly code: number | null = null,
    readonly status: number | null = null
  ) {
    super(message)
    this.name = 'ApiClientError'
  }
}

export const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 15_000
})

apiClient.interceptors.request.use(config => {
  requestStore.startRequest()
  requestStore.setLastError(null)
  const token = typeof window === 'undefined' ? null : window.sessionStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  response => {
    requestStore.finishRequest()
    return response
  },
  (error: AxiosError<unknown>) => {
    requestStore.finishRequest()
    const payload = isApiResult(error.response?.data) ? error.response?.data : null
    const message = payload?.message || error.message || '请求失败'
    const code = typeof payload?.code === 'number' ? payload.code : null
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      window.sessionStorage.removeItem('access_token')
      window.sessionStorage.removeItem('current_user')
      if (window.location.pathname !== '/login') {
        const redirect = encodeURIComponent(`${window.location.pathname}${window.location.search}`)
        window.location.assign(`/login?redirect=${redirect}`)
      }
    }
    requestStore.setLastError(message)
    return Promise.reject(new ApiClientError(message, code, error.response?.status ?? null))
  }
)

export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await apiClient.request<ApiResult<T>>(config)
  if (response.data.code !== 0) {
    const error = new ApiClientError(response.data.message, response.data.code, response.status)
    requestStore.setLastError(error.message)
    throw error
  }
  return response.data.data
}

function isApiResult(value: unknown): value is ApiResult<unknown> {
  return typeof value === 'object' && value !== null && 'code' in value && 'message' in value
}
