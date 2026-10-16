import { request } from '../api/client'
import type { BrowserWindowInfo } from '../types/browser-window'

export function getBrowserWindow(taskId: number) {
  return request<BrowserWindowInfo>({ method: 'GET', url: `/agent/tasks/${taskId}/browser-window` })
}

export function showBrowserWindow(taskId: number) {
  return request<{ command_id: string; status: string }>({ method: 'POST', url: `/agent/tasks/${taskId}/browser-window/show`, data: {} })
}
