import type { ExecutionEvidence } from '../types/execution-evidence'
import type { ResourceItem } from '../types/resource'
import { formatJsonLikeText } from './jsonFormatter'
import { isEvidenceObject, parseEvidence, redactEvidence } from './evidencePrivacy'

export function evidenceText(value: unknown, empty = '未记录'): string {
  return formatJsonLikeText(redactEvidence(value), empty)
}

export function executionEvidence(
  record: ResourceItem | null,
  fallback: { request?: unknown; assertions?: unknown } = {}
): ExecutionEvidence {
  const data = isEvidenceObject(record?.data) ? record.data : {}
  const body = parseEvidence(data.response_body)
  const api = data.case_type === 'API' || data.request != null || data.response_status != null || data.response_body != null
  const recordedAssertions = data.case_type === 'WEB' && Array.isArray(data.assertion_results) ? data.assertion_results : data.assertions
  const assertions = Array.isArray(recordedAssertions) ? recordedAssertions : fallback.assertions
  const runtime = Array.isArray(recordedAssertions)
  const input = pick(data, ['url', 'input_snapshot', 'playwright_config', 'appium_config'])
  return {
    request: redactEvidence(data.request ?? (record ? input : fallback.request ?? input)),
    response: redactEvidence(api ? pickResponse(data, body) : pick(data, [
      'url', 'step_count', 'step_timeline', 'steps', 'operation_result', 'business_result', 'error'
    ])),
    assertions: (Array.isArray(assertions) ? assertions : []).filter(isEvidenceObject).map(definition => ({
      definition: redactEvidence(definition) as Record<string, unknown>,
      outcome: runtime && typeof definition.passed === 'boolean' ? (definition.passed ? 'passed' : 'failed') : 'unknown'
    })),
    httpStatus: data.response_status,
    businessCode: redactEvidence(data.response_code ?? (isEvidenceObject(body) ? body.code : undefined)),
    duration: data.duration_ms,
    error: data.error ? evidenceText(data.error) : ''
  }
}

function pickResponse(data: Record<string, unknown>, body: unknown): unknown {
  const response = pick({ status: data.response_status, headers: data.response_headers }, ['status', 'headers'])
  if (Object.hasOwn(data, 'response_body')) return { ...(isEvidenceObject(response) ? response : {}), body }
  return response
}

function pick(data: Record<string, unknown>, keys: string[]): unknown {
  const entries = keys.filter(key => data[key] != null && data[key] !== '').map(key => [key, data[key]])
  return entries.length ? Object.fromEntries(entries) : undefined
}

export function executionStatus(status?: string): string {
  const labels: Record<string, string> = {
    success: '成功', failed: '失败', queued: '排队中', running: '执行中', blocked: '阻塞', interrupted: '中断',
    passed: '通过', skipped: '已跳过', cancelled: '已取消', canceled: '已取消', error: '异常'
  }
  return status ? labels[status] || status : '未执行'
}
