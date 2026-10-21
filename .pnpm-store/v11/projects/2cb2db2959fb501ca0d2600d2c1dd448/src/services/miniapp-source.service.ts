import { request } from '../api/client'
import { listResources } from './resource.service'
import type { SourceCase, SourceRun } from '../types/miniapp-source'
import type { ResourceItem } from '../types/resource'

const prefix = '/miniapp-testing/cases/source'

export async function listSourceCases(projectId: number) {
  const items: SourceCase[] = []
  let page = 1
  while (true) {
    const result = await listResources('/miniapp-testing/cases', { project_id: projectId, page, pageSize: 200 })
    items.push(...result.items.filter(row => row.data.execution_engine === 'source_catalog') as SourceCase[])
    if (page * 200 >= result.total) return items
    page += 1
  }
}

export async function importSourceCatalog(projectId: number, catalog: Record<string, unknown>) {
  if (!Array.isArray(catalog.cases) || !catalog.cases.length || catalog.cases.length > 500) throw new Error('测试包需包含 1 至 500 个用例')
  const total = { created_pages: 0, created_cases: 0, skipped_cases: 0, conflicts: [] as unknown[] }
  for (let index = 0; index < catalog.cases.length; index += 40) {
    const batch = await request<typeof total>({ method: 'POST', url: `${prefix}/import`,
      data: { ...catalog, cases: catalog.cases.slice(index, index + 40), project_id: projectId }, timeout: 60000 })
    total.created_pages += batch.created_pages; total.created_cases += batch.created_cases
    total.skipped_cases += batch.skipped_cases; total.conflicts.push(...batch.conflicts)
  }
  return total
}

export function createSourceRun(projectId: number, caseIds: number[], platform: string) {
  return request<SourceRun>({ method: 'POST', url: `${prefix}/runs`, data: { project_id: projectId, case_ids: caseIds, platform } })
}

export function listSourceRuns(projectId: number) {
  return request<SourceRun[]>({ method: 'GET', url: `${prefix}/runs`, params: { project_id: projectId } })
}

export function getSourceRun(runId: number) {
  return request<SourceRun>({ method: 'GET', url: `${prefix}/runs/${runId}` })
}

export function bindSourceBusiness(caseId: number, flowId: number, scenarioId: number) {
  return request<SourceCase>({ method: 'PUT', url: `${prefix}/${caseId}/business`, data: { flow_id: flowId, scenario_id: scenarioId } })
}

export function listBusinessScenarios(flowId: number) {
  return request<ResourceItem[]>({ method: 'GET', url: `/execution/flows/${flowId}/scenarios` })
}

export function executeSourceBusiness(flowId: number, scenarioId: number) {
  return request<ResourceItem>({ method: 'POST', url: `/execution/flows/${flowId}/runs`,
    data: { scenario_ids: [scenarioId], mode: 'serial', concurrency: 1, inputs: {} } })
}
