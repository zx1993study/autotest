import { request } from '../api/client'
import type { PageResult } from '../types/api'
import type { ApiReportQuery, ApiReportRow } from '../types/api-report'

export function listApiReports(params: ApiReportQuery, signal?: AbortSignal) {
  return request<PageResult<ApiReportRow>>({ url: '/api-testing/reports', params, signal })
}
