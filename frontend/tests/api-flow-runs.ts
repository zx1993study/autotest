import { createApp, h, reactive } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { apiClient } from '../src/api/client'
import ApiFlowWorkspace from '../src/components/api-flow/ApiFlowWorkspace.vue'
import type { ApiFlowRun, FlowNodeEvidence, FlowScenarioResult } from '../src/types/api-flow'

const metrics = reactive({detailRequests: 0, cancelRequests: 0})
const metadata = {project_id: 10, description: '', created_at: '', updated_at: ''}
const flow = {id: 16344, ...metadata, name: '运行结果回归', status: 'active', data: {version: 4, inputs: {}, nodes: []}}
const nodes: FlowNodeEvidence[] = Array.from({length: 35}, (_, index) => ({
  key: `node_${index}`, name: index === 30 ? '转换本场景整件与散瓶库存' : `步骤 ${index + 1}`,
  status: index === 30 ? 'failed' : index > 30 ? 'skipped' : 'success', duration_ms: 10,
  ...(index > 30 ? {reason: '前置节点失败'} : {
    response_status: 200, response_code: index === 30 ? 500 : 200,
    request: {method: 'POST', path: '/business/warehouse/230/inventory/convert', body: {sourceQuantity: 1}},
    response_body: JSON.stringify({code: index === 30 ? 500 : 200, msg: index === 30 ? '转出商品可用库存不足，当前可用：0.00' : '操作成功'}),
    assertions: [{type: 'api_rejection', passed: index !== 30, expected: 'validation', actual: {http_status: 200, code: 500}}]
  })
}))
const scenes: FlowScenarioResult[] = [
  {scenario_id: 16360, name: '正常场景', status: 'success', nodes: [{...nodes[0], name: '正常节点'}], path: ['node_0'], duration_ms: 10},
  {scenario_id: 16359, name: '审批后全部锁库、可用0时不得转换', status: 'failed', nodes, path: nodes.slice(0, 31).map(node => node.key), duration_ms: 310}
]
const runs: ApiFlowRun[] = Array.from({length: 37}, (_, index) => ({
  id: 16496 - index, ...metadata, name: `拆箱补件库存核对 - 批次 ${16496 - index}`, status: index === 1 ? 'failed' : index === 2 ? 'running' : 'success',
  data: {flow_id: 16344, template_version: 4, mode: 'serial', concurrency: 1, results: scenes.map(scene => ({...scene, nodes: []}))}
}))
apiClient.defaults.adapter = async config => {
  const path = config.url || ''
  let data: unknown = []
  if (path === '/execution/flows/16344') data = flow
  else if (path === '/execution/flows/16344/runs') data = runs
  else if (/\/runs\/\d+\/cancel$/.test(path)) {
    metrics.cancelRequests++
    runs[2].status = 'cancelled'
    data = {requested: true, message: '已请求取消，当前请求结束后停止'}
  } else if (/\/runs\/\d+$/.test(path)) {
    metrics.detailRequests++
    const batch = runs.find(run => run.id === Number(path.split('/').at(-1)))!
    data = {...batch, data: {...batch.data, results: batch.status === 'running'
      ? [{scenario_id: 16359, name: '执行中场景', status: 'running', nodes: []}]
      : batch.id === 16495 ? scenes : [scenes[0]]}}
  } else if (path.endsWith('/scenarios')) data = []
  else if (!path.endsWith('/options')) throw new Error(`Unexpected fixture request: ${path}`)
  return {data: {code: 0, message: 'success', data}, status: 200, statusText: 'OK', headers: {}, config}
}
const router = createRouter({history: createMemoryHistory(), routes: [{path: '/api/flows', component: {render: () => null}}]})
await router.push('/api/flows')
createApp({render: () => h('main', [
  h('output', {'aria-label': '回归请求计数'}, `详情请求 ${metrics.detailRequests} / 取消请求 ${metrics.cancelRequests}`),
  h(ApiFlowWorkspace, {flowId: 16344})
])}).use(router).mount('#app')
