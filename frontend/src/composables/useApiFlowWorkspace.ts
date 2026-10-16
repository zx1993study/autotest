import { computed, onBeforeUnmount, ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import * as api from '../services/api-flow.service'
import { listRemoteOptions } from '../services/resource.service'
import { cloneFlowValue } from '../types/api-flow'
import type { ApiFlow, ApiFlowRun, ApiFlowRunRequest, ApiFlowScenario, FlowDefinition } from '../types/api-flow'
import type { SelectOptionRecord } from '../types/resource'

export function useApiFlowWorkspace(flowId: number) {
  const flow = ref<ApiFlow | null>(null)
  const definition = ref<FlowDefinition>({version: 1, inputs: {}, nodes: []})
  const scenes = ref<ApiFlowScenario[]>([])
  const runs = ref<ApiFlowRun[]>([])
  const currentRun = ref<ApiFlowRun | null>(null)
  const apis = ref<SelectOptionRecord[]>([])
  const auths = ref<SelectOptionRecord[]>([])
  const selected = ref<number[]>([])
  const tab = ref('scenes')
  const busy = ref(false)
  const loading = ref(false)
  const error = ref('')
  const message = ref('')
  const editingScene = ref<ApiFlowScenario | null>(null)
  const runSceneIds = ref<number[]>([])
  const showRunDialog = ref(false)
  const dirty = computed(() => !!flow.value && JSON.stringify(definition.value) !== JSON.stringify(flow.value.data))
  const runScenes = computed(() => scenes.value.filter(scene => runSceneIds.value.includes(scene.id)))
  let timer: ReturnType<typeof setTimeout> | undefined
  let pollGeneration = 0
  let disposed = false

  async function action(work: () => Promise<void>) {
    busy.value = true; error.value = ''; message.value = ''
    try { await work() } catch (err) { error.value = err instanceof Error ? err.message : '操作失败' }
    finally { busy.value = false }
  }
  async function refreshScenes() { scenes.value = await api.listFlowScenarios(flowId) }
  async function refreshRuns() { runs.value = await api.listFlowRuns(flowId) }
  async function load() {
    loading.value = true
    await action(async () => {
      const record = await api.getApiFlow(flowId)
      flow.value = record; definition.value = cloneFlowValue(record.data)
      const options = {project_id: record.project_id}
      const values = await Promise.all([api.listFlowScenarios(flowId), api.listFlowRuns(flowId), listRemoteOptions('/api-testing/interfaces/options', options), listRemoteOptions('/project-auth/options', {...options, login_case_type: 'API'})])
      scenes.value = values[0]; runs.value = values[1]; apis.value = values[2]; auths.value = values[3]
    })
    loading.value = false
  }
  async function saveTemplate() {
    await action(async () => {
      const saved = await api.saveApiFlowTemplate(flowId, definition.value)
      flow.value = saved; definition.value = cloneFlowValue(saved.data)
      await refreshScenes(); message.value = '模板已保存'
    })
  }
  function createScene() {
    if (!flow.value) return
    error.value = ''
    editingScene.value = {id: 0, name: '', description: '', status: 'active', created_at: '', updated_at: '',
      project_id: flow.value.project_id, data: {flow_id: flowId, template_version: flow.value.data.version, inputs: {}, nodes: {}, failure_policy: 'stop', expected_end: 'auto'}}
  }
  function editScene(scene: ApiFlowScenario) { error.value = ''; editingScene.value = cloneFlowValue(scene) }
  async function saveScene(scene: ApiFlowScenario) {
    await action(async () => {
      await api.saveFlowScenario(flowId, {name: scene.name, description: scene.description, status: scene.status, data: scene.data}, scene.id || undefined)
      editingScene.value = null; await refreshScenes(); message.value = '场景已保存'
    })
  }
  async function copyScene(scene: ApiFlowScenario) { await action(async () => { await api.copyFlowScenario(flowId, scene.id); await refreshScenes(); message.value = '场景已复制' }) }
  async function toggleScene(scene: ApiFlowScenario) { await action(async () => { await api.saveFlowScenario(flowId, {name: scene.name, status: scene.status === 'active' ? 'disabled' : 'active'}, scene.id); await refreshScenes() }) }
  async function deleteScene(scene: ApiFlowScenario) {
    if (!window.confirm(`删除场景“${scene.name}”？历史运行证据仍会保留。`)) return
    await action(async () => { await api.deleteFlowScenario(flowId, scene.id); await refreshScenes() })
  }
  async function syncScene(scene: ApiFlowScenario) {
    if (!window.confirm(`将“${scene.name}”同步到模板 v${flow.value?.data.version}？已删除节点的覆盖配置会移除，其余配置将重新校验。`)) return
    await action(async () => { await api.syncFlowScenario(flowId, scene.id); await refreshScenes(); message.value = '场景已同步并通过校验' })
  }
  function openRun(ids: number[]) {
    if (dirty.value) { error.value = '模板有未保存修改，请先保存模板'; return }
    runSceneIds.value = ids; error.value = ''; showRunDialog.value = true
  }
  async function startRun(payload: ApiFlowRunRequest) {
    await action(async () => {
      currentRun.value = await api.createFlowRun(flowId, payload)
      showRunDialog.value = false; tab.value = 'runs'; await refreshRuns(); poll()
    })
  }
  async function selectRun(id: number) {
    clearTimeout(timer); pollGeneration++
    await action(async () => { currentRun.value = await api.getFlowRun(flowId, id); poll() })
  }
  async function cancelRun(id: number) { await action(async () => { const result = await api.cancelFlowRun(flowId, id); message.value = result.message; poll() }) }
  function poll() {
    clearTimeout(timer)
    const generation = ++pollGeneration
    if (!currentRun.value || !['queued', 'running'].includes(currentRun.value.status) || disposed) return
    timer = setTimeout(async () => {
      if (!currentRun.value || disposed) return
      const runId = currentRun.value.id
      try {
        const record = await api.getFlowRun(flowId, runId)
        if (generation !== pollGeneration || currentRun.value?.id !== runId || disposed) return
        currentRun.value = record
        await refreshRuns()
        if (!['queued', 'running'].includes(currentRun.value.status)) await refreshScenes()
        poll()
      } catch (err) { error.value = err instanceof Error ? err.message : '运行状态获取失败' }
    }, 1500)
  }
  onBeforeRouteLeave(() => !dirty.value || window.confirm('放弃未保存的流程模板修改？'))
  onBeforeUnmount(() => { disposed = true; clearTimeout(timer) })
  return {flow, definition, scenes, runs, currentRun, apis, auths, selected, tab, busy, loading, error, message,
    editingScene, runScenes, showRunDialog, dirty, load, saveTemplate, createScene, editScene, saveScene,
    copyScene, toggleScene, deleteScene, syncScene, openRun, startRun, selectRun, cancelRun,
    refreshRuns: () => action(refreshRuns)}
}
