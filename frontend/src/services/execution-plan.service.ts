import { request } from '../api/client'
import type { PageResult } from '../types/api'
import type {
  ExecutionPlanDetail,
  ExecutionPlanFeatureAddPayload,
  ExecutionPlanGenerationResult,
  ExecutionPlanInfo,
  ExecutionPlanManualFeaturePayload,
  ExecutionPlanSavePayload
} from '../types/execution-plan'

export function listExecutionPlans(params: Record<string, unknown>, signal?: AbortSignal) {
  return request<PageResult<ExecutionPlanInfo>>({
    method: 'GET',
    url: '/execution/plans',
    signal,
    params
  })
}

export function createExecutionPlan(payload: ExecutionPlanSavePayload) {
  return request<ExecutionPlanInfo>({
    method: 'POST',
    url: '/execution/plans',
    data: payload
  })
}

export function updateExecutionPlan(planId: number, payload: ExecutionPlanSavePayload) {
  return request<ExecutionPlanInfo>({
    method: 'PUT',
    url: `/execution/plans/${planId}`,
    data: payload
  })
}

export function deleteExecutionPlan(planId: number) {
  return request<boolean>({
    method: 'DELETE',
    url: `/execution/plans/${planId}`
  })
}

export function batchDeleteExecutionPlans(ids: number[]) {
  return request<{ deleted_count: number }>({
    method: 'POST',
    url: '/execution/plans/batch-delete',
    data: { ids }
  })
}

export function getExecutionPlanDetail(planId: number) {
  return request<ExecutionPlanDetail>({
    method: 'GET',
    url: `/execution/plans/${planId}/detail`
  })
}

export function runExecutionPlan(planId: number) {
  return request<ExecutionPlanDetail>({
    method: 'POST',
    url: `/execution/plans/${planId}/run`,
    data: {}
  })
}

export function generateExecutionPlan(planId: number) {
  return request<ExecutionPlanGenerationResult>({
    method: 'POST',
    url: `/execution/plans/${planId}/generate`,
    data: {}
  })
}

export function addExecutionPlanFeatures(planId: number, payload: ExecutionPlanFeatureAddPayload) {
  return request<ExecutionPlanDetail>({
    method: 'POST',
    url: `/execution/plans/${planId}/features`,
    data: payload
  })
}

export function addExecutionPlanManualFeature(planId: number, payload: ExecutionPlanManualFeaturePayload) {
  return request<ExecutionPlanDetail>({
    method: 'POST',
    url: `/execution/plans/${planId}/manual-features`,
    data: payload
  })
}
