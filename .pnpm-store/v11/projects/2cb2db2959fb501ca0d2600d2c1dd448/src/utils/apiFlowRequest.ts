import { cloneFlowValue } from '../types/api-flow'
import type { FlowRequestOverride } from '../types/api-flow'
import type { ResourceItem } from '../types/resource'

const requestKeys = ['method', 'path', 'api_base_path', 'content_type', 'headers', 'query', 'body', 'params']
const mergedKeys = new Set(['params', 'headers', 'query'])

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

export function flowCaseRequest(item: ResourceItem): Record<string, unknown> {
  const data = isRecord(item.data) ? item.data : {}
  const source = {...data, ...(isRecord(data.request) ? data.request : {})}
  return cloneFlowValue(Object.fromEntries(requestKeys.filter(key => key in source).map(key => [key, source[key]])))
}

export function applyFlowRequestOverride(base: Record<string, unknown>, override?: FlowRequestOverride): Record<string, unknown> {
  const result = cloneFlowValue(base)
  if (!override) return result
  for (const [key, value] of Object.entries(override.request)) {
    result[key] = mergedKeys.has(key) && isRecord(value)
      ? {...(isRecord(result[key]) ? result[key] : {}), ...cloneFlowValue(value)} : cloneFlowValue(value)
  }
  result.params = {...(isRecord(result.params) ? result.params : {}), ...cloneFlowValue(override.params)}
  for (const path of override.request_removals || []) {
    const parts = path.slice(1).split('/').map(part => part.replace(/~1/g, '/').replace(/~0/g, '~'))
    if (parts.length === 1) delete result[parts[0]!]
    else {
      const parent = result[parts[0]!]
      if (isRecord(parent)) delete parent[parts[1]!]
    }
  }
  return result
}

function pointerPart(value: string): string { return value.replace(/~/g, '~0').replace(/\//g, '~1') }
function sameValue(left: unknown, right: unknown): boolean {
  if (left === right) return true
  if (Array.isArray(left) && Array.isArray(right)) return left.length === right.length && left.every((value, index) => sameValue(value, right[index]))
  if (isRecord(left) && isRecord(right)) {
    const keys = Object.keys(left)
    return keys.length === Object.keys(right).length && keys.every(key => key in right && sameValue(left[key], right[key]))
  }
  return false
}

export function flowRequestDifference(base: Record<string, unknown>, edited: Record<string, unknown>): FlowRequestOverride {
  const delta: FlowRequestOverride = {params: {}, request: {}, request_removals: []}
  for (const section of requestKeys) {
    if (mergedKeys.has(section)) {
      const original = isRecord(base[section]) ? base[section] : {}
      const values = isRecord(edited[section]) ? edited[section] : {}
      const changes = Object.fromEntries(Object.entries(values).filter(([key, value]) => !(key in original) || !sameValue(original[key], value)))
      if (section === 'params') delta.params = changes
      else if (Object.keys(changes).length) delta.request[section] = changes
      for (const key of Object.keys(original)) {
        if (!(key in values)) delta.request_removals!.push(`/${section}/${pointerPart(key)}`)
      }
    } else if (!(section in edited)) {
      if (section in base) delta.request_removals!.push(`/${section}`)
    } else if (!(section in base) || !sameValue(base[section], edited[section])) {
      delta.request[section] = cloneFlowValue(edited[section])
    }
  }
  return delta
}

export function parseFlowRequest(text: string): Record<string, unknown> {
  const value: unknown = JSON.parse(text)
  if (!isRecord(value)) throw new Error('请求 JSON 必须是对象')
  for (const key of Object.keys(value)) {
    if (!requestKeys.includes(key)) throw new Error(`请求 JSON 不支持字段 ${key}`)
    if (mergedKeys.has(key) && !isRecord(value[key])) throw new Error(`${key} 必须是 JSON 对象`)
  }
  for (const key of ['method', 'path', 'api_base_path', 'content_type']) {
    if (key in value && typeof value[key] !== 'string') throw new Error(`${key} 必须是字符串`)
  }
  return value
}

export function isFlowRequestDraftValid(text: string): boolean {
  try { parseFlowRequest(text); return true } catch { return false }
}
