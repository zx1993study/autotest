import { createApp, h, reactive } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { apiClient } from '../src/api/client'
import MiniappSourceWorkspace from '../src/components/miniapp-testing/MiniappSourceWorkspace.vue'
import type { SourceCase, SourceRun } from '../src/types/miniapp-source'

const metadata = {project_id: 10, description: '', created_at: '', updated_at: ''}
const cases: SourceCase[] = [1, 2].map(id => ({id, ...metadata, name: id === 1 ? '登录页面呈现' : '终端客户审批通过', status: 'active', data: {
  execution_engine: 'source_catalog', category: id === 1 ? 'render' : 'business',
  definition: {id: `source-${id}`, category: id === 1 ? 'render' : 'business', automation: id === 1 ? 'scripted' : 'manual',
    route: id === 1 ? 'pages/login/index' : 'pages/customer/info', preconditions: ['仅当前批次数据'],
    steps: ['读取订单审批节点', '使用实际审批人审批'], expected: ['状态及库存正确']},
  ...(id === 2 ? {api_business: {flow_id: 30, scenario_id: 40}} : {})
}}))
const metrics = reactive({caseReads: 0, uiRuns: 0, apiRuns: 0, bindings: 0})
const runs: SourceRun[] = []
const paged = (items: unknown[]) => ({items, total: items.length, page: 1, pageSize: 200})
apiClient.defaults.adapter = async config => {
  const path = config.url || ''
  let data: unknown
  if (path === '/projects/options') data = [{id: 10, name: '隔离测试项目', is_default: true}]
  else if (path === '/miniapp-testing/cases') { metrics.caseReads++; data = paged(cases) }
  else if (path === '/execution/flows') data = paged([{id: 30, ...metadata, name: '客户审批', status: 'active', data: {}}])
  else if (path === '/execution/flows/30/scenarios') data = [{id: 40, ...metadata, name: '审批通过', status: 'active', data: {}}]
  else if (path === '/execution/flows/30/runs') { metrics.apiRuns++; data = {id: 80, status: 'queued'} }
  else if (path === '/miniapp-testing/cases/source/2/business') { metrics.bindings++; data = cases[1] }
  else if (path === '/miniapp-testing/cases/source/runs') {
    if (config.method === 'post') {
      metrics.uiRuns++
      const payload = JSON.parse(String(config.data))
      const results = cases.filter(row => payload.case_ids.includes(row.id)).map(row => ({case_id: row.id, name: row.name,
        status: 'blocked', executed: false, duration_ms: 0, reason: '未连接小程序执行节点'}))
      const run: SourceRun = {id: 90, ...metadata, name: '源码回归', status: 'blocked', data: {
        platform: payload.platform, case_count: results.length, counts: {blocked: results.length}, results}}
      runs.unshift(run); data = run
    } else data = runs.map(row => ({...row, data: {...row.data, results: []}}))
  } else if (path === '/miniapp-testing/cases/source/runs/90') data = runs[0]
  else throw new Error(`Unexpected request: ${config.method} ${path}`)
  return {data: {code: 0, message: 'success', data}, status: 200, statusText: 'OK', headers: {}, config}
}
const router = createRouter({history: createMemoryHistory(), routes: [{path: '/', component: {render: () => null}},
  {path: '/api/flows/:id', component: {render: () => null}}]})
await router.push('/')
createApp({render: () => h('main', [h('output', {'aria-label': '请求计数'},
  `列表 ${metrics.caseReads} / UI ${metrics.uiRuns} / API ${metrics.apiRuns} / 关联 ${metrics.bindings}`),
  h(MiniappSourceWorkspace)])}).use(router).mount('#app')
