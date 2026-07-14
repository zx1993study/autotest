import { request } from '../api/client'
import type {
  WebCodegenSession,
  WebCodegenStartOptions,
  WebScriptParseResult
} from '../types/web-page'

export function startWebCodegen(
  pageId: number,
  targetUrl: string,
  options: WebCodegenStartOptions = {}
) {
  const formData = new FormData()
  formData.append('page_id', String(pageId))
  formData.append('target_url', targetUrl)
  if (options.projectId) {
    formData.append('project_id', String(options.projectId))
  }
  if (options.featureType) {
    formData.append('feature_type', options.featureType)
  }
  if (options.featureName) {
    formData.append('feature_name', options.featureName)
  }
  return request<WebCodegenSession>({
    method: 'POST',
    url: '/web-testing/pages/codegen/start',
    data: formData
  })
}

export function getWebCodegenStatus(sessionId: string) {
  return request<WebCodegenSession>({
    method: 'GET',
    url: `/web-testing/pages/codegen/${sessionId}`
  })
}

export function stopWebCodegen(sessionId: string) {
  return request<WebCodegenSession>({
    method: 'POST',
    url: `/web-testing/pages/codegen/${sessionId}/stop`
  })
}

export function parseWebScript(
  projectId: number,
  pageId: number,
  sourceType: string,
  scriptText: string,
  file: File | null,
  existingElementStrategy = 'update'
) {
  const formData = new FormData()
  formData.append('project_id', String(projectId))
  formData.append('page_id', String(pageId))
  formData.append('source_type', sourceType)
  formData.append('existing_element_strategy', existingElementStrategy)
  if (scriptText.trim()) {
    formData.append('script_text', scriptText)
  }
  if (file) {
    formData.append('file', file)
  }
  return request<WebScriptParseResult>({
    method: 'POST',
    url: '/web-testing/pages/parse-script',
    data: formData
  })
}
