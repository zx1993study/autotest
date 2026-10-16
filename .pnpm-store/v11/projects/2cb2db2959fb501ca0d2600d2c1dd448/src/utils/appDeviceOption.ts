import type { SelectOptionRecord } from '../types/resource'

export function appDeviceOptionLabel(option: SelectOptionRecord) {
  const data: Record<string, unknown> = option.data && typeof option.data === 'object' && !Array.isArray(option.data) ? option.data as Record<string, unknown> : {}
  const statuses: Record<string, string> = { online: '在线', offline: '离线', unknown: '未知' }
  const state = option.status === 'disabled' ? '停用' : statuses[String(data.connection_status)] || data.connection_status
  return [option.name, data.platform, data.device_form_factor, state].filter(Boolean).join(' / ')
}
