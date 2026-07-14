/** Compatibility barrel. New code should import from services and types directly. */

export {
  batchCreateResources,
  batchDeleteResources,
  clearRemoteOptionsCache,
  createResource,
  deleteResource,
  getResource,
  listRemoteOptions,
  listRemoteOptionsCached,
  listResources,
  postAction,
  remoteOptionsCacheKey,
  updateResource
} from '../services/resource.service'
export { listProjectOptions } from '../services/project.service'
export {
  getOpenApiImportTask,
  importOpenApiFile,
  importOpenApiUrl
} from '../services/openapi.service'
export {
  getWebCodegenStatus,
  parseWebScript,
  startWebCodegen,
  stopWebCodegen
} from '../services/web-page.service'

export type { ApiResult, PageResult } from '../types/api'
export type { OpenApiImportInterface, OpenApiImportResult, OpenApiImportTask } from '../types/openapi'
export type {
  ProjectOption,
  ResourceItem,
  ResourcePayload,
  SelectOptionRecord
} from '../types/resource'
export type {
  WebCodegenSession,
  WebCodegenStartOptions,
  WebScriptParseResult
} from '../types/web-page'
