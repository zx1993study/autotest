import { request } from '../api/client'
import type { ApiCaseRunRequest } from '../types/api-case'
import type { ExecutionSummary } from '../types/execution-flow'

export function runApiCases(payload: ApiCaseRunRequest) {
  const config = { concurrency: 5, timeout: 15, ...payload.config }
  const caseIds = [...new Set(payload.case_ids)]
  const concurrency = Math.max(1, Math.min(10, config.concurrency))
  const waves = Math.ceil(caseIds.length / concurrency)
  const waitTimeout = Math.max(60_000, waves * config.timeout * 1000 + caseIds.length * 2000 + 30_000)
  return request<ExecutionSummary>({
    method: 'POST', url: '/api-testing/cases/run',
    data: { ...payload, case_ids: caseIds, config }, timeout: waitTimeout
  })
}
