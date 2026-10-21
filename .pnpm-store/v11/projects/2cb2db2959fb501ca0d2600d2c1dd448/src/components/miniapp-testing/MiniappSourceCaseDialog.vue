<template>
  <div class="mini-backdrop" @click.self="emit('close')"><section class="mini-dialog" role="dialog" aria-modal="true" aria-label="小程序用例详情" @keydown.esc="emit('close')">
    <header><h3>#{{ item.id }} {{ item.name }}</h3><button title="关闭" aria-label="关闭" @click="emit('close')"><X :size="18" /></button></header>
    <p>{{ item.data.definition?.id }} · {{ item.data.definition?.route }}</p>
    <h4>前置条件</h4><ul><li v-for="text in item.data.definition?.preconditions" :key="text">{{ text }}</li></ul>
    <h4>业务步骤</h4><ol><li v-for="text in item.data.definition?.steps" :key="text">{{ text }}</li></ol>
    <h4>预期结果</h4><ul><li v-for="text in item.data.definition?.expected" :key="text">{{ text }}</li></ul>
    <h4>关联 API 业务流程</h4>
    <div class="mini-toolbar"><select v-model.number="flowId" aria-label="API 功能" :disabled="busy"><option :value="0">选择功能流程</option><option v-for="flow in flows" :key="flow.id" :value="flow.id">#{{ flow.id }} {{ flow.name }}</option></select>
      <select v-model.number="scenarioId" aria-label="API 场景" :disabled="busy || !flowId"><option :value="0">选择场景</option><option v-for="scene in scenes" :key="scene.id" :value="scene.id">#{{ scene.id }} {{ scene.name }}</option></select>
      <button :disabled="busy || !scenarioId" @click="save"><Link :size="16" />保存关联</button></div>
    <div v-if="item.data.api_business" class="mini-toolbar"><RouterLink :to="`/api/flows/${item.data.api_business.flow_id}`">查看业务流程</RouterLink><button :disabled="busy" @click="runBusiness"><Play :size="16" />执行 API 场景</button></div>
    <p v-if="message" role="status">{{ message }}</p><p v-if="error" role="alert" class="mini-error">{{ error }}</p>
  </section></div>
</template>
<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { Link, Play, X } from 'lucide-vue-next'
import { bindSourceBusiness, executeSourceBusiness, listBusinessScenarios } from '../../services/miniapp-source.service'
import { listResources } from '../../services/resource.service'
import type { SourceCase } from '../../types/miniapp-source'
import type { ResourceItem } from '../../types/resource'
const props = defineProps<{ item: SourceCase }>()
const emit = defineEmits<{ (event: 'close'): void; (event: 'saved', value: SourceCase): void }>()
const flowId = ref(props.item.data.api_business?.flow_id || 0)
const scenarioId = ref(0)
const flows = ref<ResourceItem[]>([])
const scenes = ref<ResourceItem[]>([])
const busy = ref(false)
const error = ref('')
const message = ref('')
let revision = 0
onMounted(async () => {
  try { flows.value = (await listResources('/execution/flows', { project_id: props.item.project_id, pageSize: 200 })).items }
  catch (cause) { error.value = String(cause) }
})
watch(flowId, async value => {
  const current = ++revision
  scenes.value = []; scenarioId.value = 0
  if (!value) return
  try {
    const rows = await listBusinessScenarios(value)
    if (current !== revision) return
    scenes.value = rows.filter(row => row.status === 'active')
    if (value === props.item.data.api_business?.flow_id) scenarioId.value = props.item.data.api_business.scenario_id
  } catch (cause) { if (current === revision) error.value = String(cause) }
}, { immediate: true })
onBeforeUnmount(() => { revision++ })
async function save() {
  busy.value = true; error.value = ''; message.value = ''
  try { emit('saved', await bindSourceBusiness(props.item.id, flowId.value, scenarioId.value)); message.value = '业务流程已关联' }
  catch (cause) { error.value = String(cause) }
  finally { busy.value = false }
}
async function runBusiness() {
  const binding = props.item.data.api_business
  if (!binding || !window.confirm('确认执行该 API 场景？它可能写入业务数据。仅应选择已配置测试数据隔离的场景。API 结果不会计为 UI 通过。')) return
  busy.value = true; error.value = ''; message.value = ''
  try {
    const run = await executeSourceBusiness(binding.flow_id, binding.scenario_id)
    message.value = `API 批次 #${run.id} 已提交，可在关联业务流程的运行记录中查看。`
  } catch (cause) { error.value = String(cause) }
  finally { busy.value = false }
}
</script>
