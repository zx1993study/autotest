<template>
  <Teleport to="body">
  <div v-if="visible" class="modal-backdrop" @click.self="emit('close')">
    <section class="modal-panel vision-dialog" role="dialog" aria-modal="true" aria-labelledby="vision-dialog-title">
      <header class="modal-header">
        <div><h3 id="vision-dialog-title">AI 功能发现</h3><p>{{ feature?.name }}</p></div>
        <button class="modal-close" type="button" aria-label="关闭" @click="emit('close')">&times;</button>
      </header>
      <form class="modal-form" @submit.prevent="start">
        <div class="target-page"><span>分析页面</span><code>{{ feature?.data.route || feature?.data.url }}</code></div>
        <fieldset class="mode-options" :disabled="flow.active.value || flow.submitting.value">
          <legend>执行模式</legend>
          <label :class="{ selected: !form.headless }"><input v-model="form.headless" type="radio" :value="false" /><Monitor :size="16" />本地有头</label>
          <label :class="{ selected: form.headless }"><input v-model="form.headless" type="radio" :value="true" /><MonitorOff :size="16" />服务器无头</label>
        </fieldset>
        <fieldset class="form-grid" :disabled="flow.active.value || flow.submitting.value">
          <label v-if="!form.headless" class="field full"><span>执行节点</span>
            <select v-model="form.nodeKey" required><option value="">请选择在线 Web 节点</option><option v-for="node in nodes" :key="node.id" :value="node.data.node_key">{{ node.name }}</option></select>
          </label>
          <label class="field full"><span>视觉模型</span>
            <div class="model-control"><select v-model="form.modelId"><option value="">当前视觉模型</option><option v-for="model in models" :key="model.id" :value="model.id">{{ model.name }} · {{ model.data.model }}</option></select>
              <button type="button" :disabled="checking" title="检测模型图片输入与 JSON 输出" @click="checkModel"><FlaskConical :size="16" />{{ checking ? '检测中' : '检测模型' }}</button>
            </div>
          </label>
          <label v-if="!form.headless && !loginTarget" class="field checkbox-field full"><input v-model="form.waitForLogin" type="checkbox" /><span>等待手动登录（验证码）</span></label>
          <label v-if="!form.headless && !loginTarget" class="field checkbox-field full"><input v-model="form.reuseLogin" type="checkbox" /><span>复用本机登录态</span></label>
          <label class="field"><span>最多发现功能数</span><input v-model.number="form.maxFunctions" type="number" min="1" max="30" /></label>
          <label class="field checkbox-field"><input v-model="form.includeDestructive" type="checkbox" /><span>包含删除类功能</span></label>
          <label class="field full"><span>操作范围与预期结果</span><textarea v-model="form.userPrompt" rows="4" /></label>
        </fieldset>
        <p v-if="loadError" class="form-error" role="alert">{{ loadError }}</p>
        <p v-if="checkResult" :class="checkResult.healthy ? 'model-ok' : 'form-error'" role="status">{{ checkResult.model_name }}：{{ checkResult.message }}（{{ checkResult.model_http_calls }} 次请求）</p>
        <div v-if="flow.submission.value" class="task-progress" role="status">
          <div>任务 #{{ flow.submission.value.task_id }} · {{ flow.submission.value.model_name }}</div>
          <div>{{ flow.progress.value || statusText }}</div>
          <div>模型 HTTP 调用：{{ flow.calls.value }} 次</div>
          <BrowserWindowPanel v-if="flow.submission.value.agent_task_id" :task-id="flow.submission.value.agent_task_id" />
          <div v-if="flow.waiting.value" class="login-actions">
            <button type="button" :disabled="flow.confirming.value" @click="flow.confirm('continue')">登录已完成，继续发现</button>
          </div>
        </div>
        <p v-if="flow.error.value" class="form-error" role="alert">{{ flow.error.value }}</p>
        <footer class="modal-actions">
          <RouterLink v-if="flow.submission.value" to="/execution/generation-tasks">查看生成记录</RouterLink>
          <button type="button" @click="emit('close')">关闭</button>
          <button v-if="flow.active.value" type="button" :disabled="flow.confirming.value" @click="cancel"><Square :size="14" />{{ flow.confirming.value ? '正在中止' : '中止分析' }}</button>
          <button type="submit" :disabled="loading || flow.active.value || flow.submitting.value || (!form.headless && !form.nodeKey)">{{ flow.active.value ? '发现执行中' : flow.submitting.value ? '提交中...' : '开始发现' }}</button>
        </footer>
      </form>
    </section>
  </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { FlaskConical, Monitor, MonitorOff, Square } from 'lucide-vue-next'
import { listAgentNodes } from '../../services/agent.service'
import { listResources } from '../../services/resource.service'
import { activeWebVision, checkVisionModel } from '../../services/web-vision.service'
import { getErrorMessage } from '../../utils/error-message'
import type { AgentNode } from '../../types/agent'
import type { ResourceItem } from '../../types/resource'
import type { WebPageFeature } from '../../types/web-page'
import type { VisionModelCheck } from '../../types/web-vision'
import { useWebVisionDiscovery } from './useWebVisionDiscovery'
import BrowserWindowPanel from '../execution/BrowserWindowPanel.vue'
import { isLoginTarget } from '../../utils/webDiscoveryTarget'

const props = defineProps<{ visible: boolean; projectId: number; feature: WebPageFeature | null }>()
const emit = defineEmits<{ close: []; completed: [] }>()
const flow = useWebVisionDiscovery(() => emit('completed'))
const loginTarget = computed(() => isLoginTarget(String(props.feature?.data.route || '')) || isLoginTarget(String(props.feature?.data.url || '')))
const form = reactive({ headless: false, nodeKey: '', modelId: '' as string | number, waitForLogin: true, reuseLogin: true, maxFunctions: 8, includeDestructive: true, userPrompt: '' })
const models = ref<ResourceItem[]>([])
const nodes = ref<AgentNode[]>([])
const loading = ref(false)
const loadError = ref('')
const checking = ref(false)
const checkResult = ref<VisionModelCheck | null>(null)
const statusText = computed(() => ({ success: '发现完成', partial_success: '部分完成', failed: '发现失败', canceled: '已中止' }[flow.task.value?.status || ''] || flow.task.value?.status || '等待执行'))
let openedFeature = 0
let loadVersion = 0

watch(() => [props.visible, props.feature?.id], async () => {
  const version = ++loadVersion
  if (!props.visible || !props.feature) { flow.stop(); return }
  if (openedFeature !== props.feature.id) { flow.reset(); checkResult.value = null; openedFeature = props.feature.id; form.userPrompt = props.feature.description || ''; form.waitForLogin = !loginTarget.value; form.reuseLogin = !loginTarget.value }
  flow.resume()
  loading.value = true
  loadError.value = ''
  try {
    const modelResult = await listResources('/system/model-configs', { page: 1, pageSize: 100 })
    const nodeResult = await listAgentNodes({ page: 1, pageSize: 100 })
    const existing = await activeWebVision(props.projectId, props.feature.id)
    if (version !== loadVersion) return
    models.value = modelResult.items.filter(m => m.status === 'active' && m.data.supports_vision === true)
    nodes.value = nodeResult.items.filter(n => n.status === 'active' && ['online', 'busy'].includes(n.data.agent_status) && n.data.capabilities?.includes('web_vision_discovery') && Date.now() - Date.parse(n.data.last_seen_at || '') < 90_000)
    if (!nodes.value.some(n => n.data.node_key === form.nodeKey)) form.nodeKey = (nodes.value.find(n => n.data.default_local_headed) || nodes.value[0])?.data.node_key || ''
    if (existing && !flow.active.value) flow.resume(existing)
  } catch (exception) { if (version === loadVersion) loadError.value = getErrorMessage(exception) }
  finally { if (version === loadVersion) loading.value = false }
}, { immediate: true })

function start() {
  if (!props.feature) return
  void flow.start({ project_id: props.projectId, page_id: props.feature.id, vision_model_id: Number(form.modelId) || null, headless: form.headless, node_key: form.headless ? undefined : form.nodeKey, wait_for_login: !loginTarget.value && !form.headless && form.waitForLogin, reuse_login: !loginTarget.value && form.reuseLogin, max_functions: form.maxFunctions, include_destructive: form.includeDestructive, user_prompt: form.userPrompt })
}

function cancel() { if (window.confirm('中止本次 AI 分析？')) void flow.confirm('cancel') }

async function checkModel() {
  checking.value = true
  checkResult.value = null
  try { checkResult.value = await checkVisionModel(Number(form.modelId) || null) }
  catch (exception) { loadError.value = getErrorMessage(exception) }
  finally { checking.value = false }
}
</script>

<style scoped>
.modal-backdrop { z-index: 1300; }
.vision-dialog { width: min(620px, calc(100vw - 32px)); }
.target-page { display: flex; gap: 12px; margin-bottom: 14px; overflow-wrap: anywhere; }
.target-page code { min-width: 0; }
.modal-actions button { display: inline-flex; align-items: center; gap: 6px; }
fieldset { border: 0; padding: 0; margin: 0 0 14px; min-width: 0; }
.mode-options { display: flex; flex-wrap: wrap; gap: 8px; }
.mode-options legend { margin-bottom: 8px; font-weight: 600; }
.mode-options label { display: flex; align-items: center; gap: 6px; padding: 8px 12px; border: 1px solid #d5deec; border-radius: 4px; white-space: nowrap; }
.mode-options input { width: 14px; height: 14px; padding: 0; margin: 0; flex: 0 0 auto; }
.mode-options svg { flex: 0 0 auto; }
.mode-options label.selected { border-color: #087a87; background: #edf9f7; }
.model-control { display: flex; gap: 8px; min-width: 0; }
.model-control select { flex: 1; min-width: 0; }
.model-control button { display: inline-flex; align-items: center; gap: 5px; white-space: nowrap; }
.task-progress { padding: 10px 0; border-top: 1px solid #e5eaf2; line-height: 1.7; overflow-wrap: anywhere; }
.login-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.model-ok { color: #137b49; }
.form-error { overflow-wrap: anywhere; }
@media (max-width: 480px) { .model-control { flex-wrap: wrap; } .model-control select { flex-basis: 100%; } }
</style>
