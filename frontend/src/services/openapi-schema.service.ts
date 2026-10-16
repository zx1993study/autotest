import { request } from '../api/client'
import type {
  OpenApiCaseGenerationPayload,
  OpenApiCaseGenerationResult,
  OpenApiCasePreview,
  OpenApiSchemaSnapshot
} from '../types/openapi-schema'

export function getLatestOpenApiSchema(projectId: number) {
  return request<OpenApiSchemaSnapshot>({
    method: 'GET',
    url: '/api-testing/interfaces/schema-snapshots/latest',
    params: { project_id: projectId }
  })
}

export function previewOpenApiCases(payload: OpenApiCaseGenerationPayload) {
  return request<OpenApiCasePreview>({
    method: 'POST',
    url: '/api-testing/case-drafts/openapi/preview',
    data: payload
  })
}

export function generateOpenApiCases(payload: OpenApiCaseGenerationPayload) {
  return request<OpenApiCaseGenerationResult>({
    method: 'POST',
    url: '/api-testing/case-drafts/openapi/generate',
    data: payload
  })
}
