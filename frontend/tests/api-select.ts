import { createApp, h, ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import ApiSelect from '../src/components/common/ApiSelect.vue'
import ResourcePage from '../src/components/ResourcePage.vue'
import ProjectAuthLoginCasePicker from '../src/components/projects/ProjectAuthLoginCasePicker.vue'
import ExecutionDashboardPage from '../src/views/execution/ExecutionDashboardPage.vue'
import ExecutionFlowDetailPage from '../src/views/execution/ExecutionFlowDetailPage.vue'
import { apiSourceInterfaceField, apiInterfaceSelectField } from '../src/resource-schemas/shared'
import type { SelectOptionRecord } from '../src/types/resource'
import '../src/styles/index.css'

const mode = new URLSearchParams(window.location.search).get('mode') || 'control'
const router = createRouter({history: createMemoryHistory(), routes: [{path: '/flows/:flowId', component: {render: () => null}}]})
await router.push('/flows/1')
const options: SelectOptionRecord[] = [
  {id: 10, name: '新增客户', method: 'POST', path: '/customers'},
  {id: 11, name: '查询客户', method: 'GET', path: '/customers/detail'},
  {id: 12, name: '查询客户', method: 'GET', path: '/customers/detail'},
  {id: 13, name: '更新 Profile', data: {method: 'PATCH', path: '/users/profile'}},
  ...Array.from({length: 35}, (_, index) => ({id: 100 + index, name: `接口 ${index}`, method: 'GET', path: `/long/path/${index}`}))
]

createApp({
  setup() {
    const selected = ref(10)
    const changes = ref<number[]>([])
    const disabled = ref(false)
    const loading = ref(false)
    const empty = ref(false)
    const required = ref(false)
    const selectedCase = ref<number | null>(101)
    const project = ref(1)
    const buttons = [
      ['reset', '重置', () => { selected.value = 10; changes.value = [] }],
      ['external', '外部更新', () => { selected.value = 13 }],
      ['disabled', '禁用', () => { disabled.value = !disabled.value }],
      ['loading', '加载', () => { loading.value = !loading.value }],
      ['empty', '空列表', () => { empty.value = !empty.value }],
      ['required', '必填', () => { required.value = !required.value }],
      ['unavailable', '无效选项', () => { selected.value = 999 }]
    ] as const
    return () => h('main', {style: 'box-sizing:border-box;width:min(100%,900px);padding:16px;margin:auto;'}, [
      mode === 'dashboard' ? h(ExecutionDashboardPage) :
      mode === 'step' ? h(ExecutionFlowDetailPage) :
      mode === 'auth' ? h('form', [
        h(ProjectAuthLoginCasePicker, {modelValue: selectedCase.value, projectId: project.value, caseType: 'API', required: true,
          'onUpdate:modelValue': value => { selectedCase.value = value }}),
        h('output', {id: 'selected-case'}, String(selectedCase.value)),
        h('button', {id: 'project', type: 'button', onClick: () => { project.value = project.value === 1 ? 2 : 1 }}, '切换项目')
      ]) :
      mode === 'resource' ? h(ResourcePage, {title: '接口选择测试', description: '', apiPath: '/api-testing/cases',
        fields: [{key: 'name', label: '名称', type: 'text', required: true}, apiSourceInterfaceField, apiInterfaceSelectField],
        defaultValues: {name: '测试用例', source_id: 10, data: {interface_id: 11}}, showJsonEditor: false}) :
      h('form', {onSubmit: (event: Event) => event.preventDefault()}, [
        h('label', {class: 'field'}, [h('span', '测试 API'), h(ApiSelect, {modelValue: selected.value,
          options: empty.value ? [] : options, label: '测试 API', disabled: disabled.value, loading: loading.value, required: required.value,
          'onUpdate:modelValue': value => { selected.value = value }, onChange: value => { changes.value.push(value) }})]),
        h('output', {id: 'selected'}, String(selected.value)), h('output', {id: 'changes'}, JSON.stringify(changes.value)),
        h('div', {style: 'display:flex;flex-wrap:wrap;gap:8px;margin-top:16px;'}, buttons.map(([id, label, action]) => h('button', {id, type: 'button', onClick: action}, label))),
        h('button', {id: 'outside', type: 'button', style: 'margin-top:16px;'}, '其他字段')
      ])
    ])
  }
}).use(router).mount('#app')
