<template>
  <section>
    <header class="toolbar"><h2>生成记录</h2><ProjectFilterSelect v-model="projectId" @ready="projectReady = true" /><button type="button" title="刷新" aria-label="刷新" :disabled="loading" @click="load"><RefreshCw :size="16" /></button></header>
    <p v-if="error" role="alert">{{ error }}</p>
    <div class="table-wrap"><table>
      <thead><tr><th>名称</th><th>领域</th><th>状态</th><th>进度</th><th>模型调用</th><th>操作</th></tr></thead>
      <tbody><tr v-if="loading"><td colspan="6">正在加载...</td></tr><tr v-for="t in tasks" :key="t.id"><td>{{ t.name }}</td><td>{{ t.data.domain || 'WEB' }}</td><td>{{ t.status === 'canceled' ? '已中止' : t.status }}</td><td>{{ t.data.progress }}</td><td>{{ t.data.model_http_calls || 0 }}</td><td><button type="button" @click="open(t)">查看</button><button v-if="t.data.task_type === 'business_generation'" type="button" @click="review(t)">审阅</button><button v-if="t.data.task_type === 'web_vision_discovery' && ['queued', 'pending', 'running'].includes(t.status)" type="button" :disabled="canceling === t.id" @click="cancel(t)"><Square :size="14" />中止</button></td></tr><tr v-if="!loading && !error && !tasks.length"><td colspan="6">暂无记录</td></tr></tbody>
    </table></div>
    <CommonPagination :page="page" :page-size="pageSize" :total="total" :loading="loading" @change="paginate" />
    <GenerationTaskDetailModal :visible="!!detail" :loading="false" error="" :task="detail" @close="detail = null" />
    <BusinessGenerationDrawer v-if="current" :key="current.id" :visible="reviewVisible" :domain="current.data.domain" :source-id="current.data.source_id" :source-name="current.name" @close="reviewVisible = false" @saved="load" />
  </section>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue'
import { RefreshCw, Square } from 'lucide-vue-next'
import ProjectFilterSelect from '../../components/filters/ProjectFilterSelect.vue'
import CommonPagination from '../../components/common/CommonPagination.vue'
import GenerationTaskDetailModal from '../../components/execution/GenerationTaskDetailModal.vue'
import BusinessGenerationDrawer from '../../components/generation/BusinessGenerationDrawer.vue'
import { listResources } from '../../api/http'
import { getGeneration, generationPath } from '../../services/business-generation.service'
import type { ResourceItem } from '../../types/resource'
import type { GenerationTask } from '../../types/generation'
import { cancelWebVision } from '../../services/web-vision.service'
import { useLatestRequest } from '../../composables/useLatestRequest'
const projectId = ref(0), projectReady = ref(false), page = ref(1), pageSize = ref(20), total = ref(0)
const { loading, error, run: loadRequest } = useLatestRequest('生成记录加载失败')
const tasks = ref<GenerationTask[]>([]), detail = ref<ResourceItem | null>(null), current = ref<GenerationTask | null>(null), reviewVisible = ref(false)
const canceling = ref<number | null>(null)
async function load() {
  if (!projectReady.value) return
  await loadRequest(signal => listResources(generationPath, {
    project_id: projectId.value || undefined, page: page.value, pageSize: pageSize.value
  }, signal), result => { tasks.value = result.items as unknown as GenerationTask[]; total.value = result.total })
}
async function open(task: ResourceItem) { try { detail.value = await getGeneration(task.id) } catch (e) { error.value = String(e) } }
function review(task: GenerationTask) { current.value = task; sessionStorage.setItem(`generation:${task.data.domain}:${task.data.source_id}`, String(task.id)); reviewVisible.value = true }
async function cancel(task: GenerationTask) {
  if (!window.confirm('中止本次 AI 分析？')) return
  canceling.value = task.id
  try { await cancelWebVision(task.id); await load() }
  catch (e) { error.value = String(e) }
  finally { canceling.value = null }
}
function paginate(p: number, size: number) { page.value = p; pageSize.value = size; load() }
watch([projectId, projectReady], () => {
  if (!projectReady.value) return
  page.value = 1; tasks.value = []; total.value = 0; void load()
})
</script>
<style scoped>
.toolbar { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; } h2 { margin: 0 auto 0 0; font-size: 18px; } p { color: #b42318; }
</style>
