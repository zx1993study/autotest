import { request } from '../api/client'

export interface DynamicValueSnapshot {
  generated_at_ms: number
  values: Record<string, unknown>
  templates: Record<string, string>
}

export function previewDynamicValue(value: unknown, variables: Record<string, unknown> = {}) {
  return request<{ resolved: unknown; dynamic_values: DynamicValueSnapshot }>({
    method: 'POST', url: '/testing/dynamic-values/preview', data: { value, variables }
  })
}
