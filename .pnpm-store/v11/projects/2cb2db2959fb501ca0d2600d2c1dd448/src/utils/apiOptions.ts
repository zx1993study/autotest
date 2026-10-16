import type { SelectOptionRecord } from '../types/resource'

function apiData(option: SelectOptionRecord): Record<string, unknown> {
  const value = option.data
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

export function apiOptionLabel(option: SelectOptionRecord): string {
  const data = apiData(option)
  const method = String(option.method || data.method || data.api_method || '').toUpperCase()
  const path = String(option.path || data.path || data.api_path || '')
  const name = String(option.name || '')
  return [method, path, name].filter(Boolean).join(' ') || `#${option.id}`
}

export function apiOptionMatches(option: SelectOptionRecord, query: string): boolean {
  const terms = query.normalize('NFKC').trim().toLowerCase().split(/\s+/).filter(Boolean)
  const text = `${apiOptionLabel(option)} ${option.id}`.normalize('NFKC').toLowerCase()
  return terms.every(term => text.includes(term))
}

export function filterApiOptions(options: SelectOptionRecord[], query: string): SelectOptionRecord[] {
  return options.filter(option => apiOptionMatches(option, query))
}
