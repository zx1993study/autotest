import { request } from '../api/client'
import type { AppExploration } from '../types/app-exploration'

const root = (featureId:number) => `/app-testing/features/${featureId}/exploration`
export function startAppExploration(featureId:number,payload:Record<string,unknown>) {
  return request<AppExploration>({method:'POST',url:root(featureId),data:payload})
}
export function activeAppExploration(featureId:number) {
  return request<AppExploration|null>({method:'GET',url:`${root(featureId)}/active`})
}
export function getAppExploration(featureId:number,id:number) {
  return request<AppExploration>({method:'GET',url:`${root(featureId)}/${id}`})
}
export function controlAppExploration(featureId:number,id:number,payload:Record<string,unknown>) {
  return request<AppExploration>({method:'POST',url:`${root(featureId)}/${id}/control`,data:payload})
}
export function acceptAppExploration(featureId:number,id:number,name:string) {
  return request<{id:number;domain:string}>({method:'POST',url:`${root(featureId)}/${id}/accept`,data:{name}})
}
