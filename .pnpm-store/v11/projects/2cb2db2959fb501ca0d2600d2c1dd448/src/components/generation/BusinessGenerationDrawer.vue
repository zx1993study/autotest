<template>
  <div v-if="visible" class="generation-backdrop" @click.self="$emit('close')">
    <section class="generation-drawer" :class="{ expanded }" role="dialog" aria-modal="true" aria-labelledby="generation-title">
      <header><h3 id="generation-title">{{ domain }} 生成对话</h3><button type="button" title="新对话" aria-label="新对话" :disabled="busy || verifying" @click="newConversation"><MessageSquarePlus :size="18" /></button><button type="button" :title="expanded ? '还原窗口' : '展开窗口'" aria-label="展开或还原窗口" @click="expanded = !expanded"><Minimize2 v-if="expanded" :size="18" /><Maximize2 v-else :size="18" /></button><button type="button" title="关闭" aria-label="关闭" @click="$emit('close')"><X :size="18" /></button></header>
      <div class="mobile-tabs"><button type="button" :class="{ active:mobilePane === 'chat' }" @click="mobilePane = 'chat'">对话</button><button type="button" :class="{ active:mobilePane === 'result' }" @click="mobilePane = 'result'">步骤与脚本</button></div>
      <div class="conversation-workspace">
      <section class="conversation-pane" :class="{ 'mobile-hidden':mobilePane !== 'chat' }">
        <p class="scope">{{ sourceName }}</p>
        <div v-if="domain !== 'API'" class="modes"><label><input v-model="mode" type="radio" value="text" :disabled="busy" />自然语言</label><label><input v-model="mode" type="radio" value="screenshots" :disabled="busy" />截图复现</label></div>
        <label>模型<select v-model="modelId" :disabled="busy"><option :value="null">当前模型</option><option v-for="m in models" :key="m.id" :value="m.id">{{ m.name }}</option></select></label>
        <label class="check"><input v-model="includeKnowledge" type="checkbox" :disabled="busy" />引用已验证知识</label>
        <div v-if="mode === 'screenshots' && !busy" class="attachments"><ReferenceScreenshots v-model="screenshots" /></div>
        <GenerationConversation v-model="prompt" :messages="task?.data.conversation || []" :busy="busy || verifying" :progress="task?.data.progress" :error="error" @send="generate" />
      </section>
      <main :class="{ 'mobile-hidden':mobilePane !== 'result' }">
        <div v-if="task" class="task-state" role="status"><strong>{{ task.data.progress || task.status }}</strong><span>模型 HTTP 调用 {{ task.data.model_http_calls || 0 }} 次</span><RouterLink to="/execution/generation-tasks">生成记录</RouterLink></div>
        <GenerationExecutionSteps :stages="task?.data.stages" :status="task?.status" :candidate="candidate" :records="verification?.result?.records" />
        <p v-if="task?.data.error" class="error">{{ task.data.error }}</p>
        <ul v-if="task?.data.result?.questions?.length" class="warnings"><li v-for="q in task.data.result.questions" :key="String(q)">{{ q }}</li></ul>
        <ul v-if="task?.data.result?.warnings?.length" class="warnings"><li v-for="w in task.data.result.warnings" :key="String(w)">{{ w }}</li></ul>
        <GenerationCandidateEditor v-if="candidate" v-model="candidate" :domain="domain" @valid="editorValid = $event" />
        <section v-if="task?.data.repair_changes?.length"><h4>定位修复对比</h4><pre v-for="c in task.data.repair_changes" :key="c.step">步骤 {{ c.step }}
{{ JSON.stringify(c.before) }}
→ {{ JSON.stringify(c.after) }}</pre></section>
        <section v-if="domain === 'WEB' && candidate" class="verification">
          <label>执行节点<select v-model="nodeKey"><option value="">选择本地 Agent</option><option v-for="n in nodes" :key="n.id" :value="n.data.node_key">{{ n.name }}</option></select></label>
          <label class="check"><input v-model="waitLogin" type="checkbox" />等待人工登录</label>
          <label class="check"><input v-model="approveEffects" type="checkbox" />确认允许候选中的点击、输入、提交操作</label>
          <p v-if="verification">验证状态：{{ verification.phase === 'waiting_login' ? '等待人工登录' : verification.status }}</p>
          <BrowserWindowPanel v-if="task?.data.agent_task_id" :task-id="Number(task.data.agent_task_id)" />
          <WebOperationControls :task="agentTask" />
          <button v-if="verification?.phase === 'waiting_login' && verification?.status === 'running'" type="button" @click="control('continue')">登录完成，继续</button>
          <div v-if="verification?.result?.records?.length">
            <p v-for="r in verification.result.records" :key="r.id || r.name" :class="{ error: r.status === 'failed' }">{{ r.data.error || r.data.result_label || `${r.data.step_count} 个步骤通过` }}<span v-if="r.data.privacy_notice"> · {{ r.data.privacy_notice }}</span></p>
            <a v-for="s in evidence" :key="s.screenshot_url" :href="mediaUrl(s.screenshot_url)" target="_blank" rel="noopener noreferrer"><img :src="mediaUrl(s.screenshot_url)" :alt="`步骤 ${s.step_order} 截图`" /></a>
            <video v-if="videoUrl" :src="mediaUrl(videoUrl)" controls preload="metadata" />
          </div>
        </section>
      </main></div>
      <footer>
        <button v-if="busy || verifying" type="button" @click="control('cancel')">取消任务</button>
        <button v-if="domain === 'WEB' && candidate" type="button" :disabled="busy || verifying || !nodeKey || !editorValid || saved" @click="verify">验证复现</button>
        <button v-if="candidate" type="button" :disabled="busy || verifying || !editorValid || saved || (domain !== 'WEB' && !!task?.data.result?.questions?.length) || (requiresVerifiedRepair && verification?.status !== 'success')" @click="accept">{{ saved ? '已保存' : domain === 'APP' ? '保存场景' : domain === 'WEB' ? '保存功能脚本' : '保存草稿' }}</button>
        <button v-if="verification?.status === 'failed' && !saved" type="button" :disabled="busy" @click="repair">分析失败并生成修复候选</button>
        <button v-if="domain === 'WEB' && saved" type="button" :disabled="busy" @click="exportScript">导出脚本包</button>
      </footer>
    </section>
  </div>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { X, MessageSquarePlus, Maximize2, Minimize2 } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import { listResources } from '../../api/http'
import type { ResourceItem } from '../../types/resource'
import type { GenerationTask } from '../../types/generation'
import { listAgentNodes } from '../../services/agent.service'
import type { AgentNode } from '../../types/agent'
import { generationAction, generationScript, getGeneration, submitGeneration, type GenerationDomain, type ReferenceImage } from '../../services/business-generation.service'
import { withScreenshotAccessToken as mediaUrl } from '../../utils/screenshotUrl'
import ReferenceScreenshots from './ReferenceScreenshots.vue'
import GenerationCandidateEditor from './GenerationCandidateEditor.vue'
import BrowserWindowPanel from '../execution/BrowserWindowPanel.vue'
import WebOperationControls from '../web-testing/WebOperationControls.vue'
import { getAgentTask } from '../../services/agent.service'
import type { AgentTask } from '../../types/agent'
import { downloadBundle } from '../../utils/downloadBundle'
import GenerationConversation from './GenerationConversation.vue'
import GenerationExecutionSteps from './GenerationExecutionSteps.vue'
const props = defineProps<{ visible: boolean; domain: GenerationDomain; sourceId: number; sourceName: string; initialTaskId?: number; initialPrompt?: string }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const prompt = ref(''), error = ref(''), mode = ref('text'), nodeKey = ref('')
const expanded = ref(false)
const mobilePane = ref('chat')
const modelId = ref<number | null>(null), includeKnowledge = ref(true), waitLogin = ref(true), approveEffects = ref(false)
const screenshots = ref<ReferenceImage[]>([]), models = ref<ResourceItem[]>([]), nodes = ref<AgentNode[]>([])
const task = ref<GenerationTask | null>(null), candidate = ref<Record<string, any> | null>(null), editorValid = ref(true), saving = ref(false)
const agentTask = ref<AgentTask | null>(null)
const verification = computed(() => task.value?.data.verification)
const verifying = computed(() => ['pending', 'running'].includes(verification.value?.status || ''))
const saved = computed(() => !!task.value?.data.saved_resource)
const requiresVerifiedRepair = computed(() => Boolean(task.value?.data.repair_case_id || task.value?.data.repair_parent_id))
const busy = computed(() => saving.value || ['queued', 'running'].includes(task.value?.status || ''))
const evidence = computed(() => (verification.value?.result?.records || []).flatMap((r: any) => r.data?.screenshots || []).filter((s: any) => s.screenshot_url))
const videoUrl = computed(() => verification.value?.result?.records?.[0]?.data?.video_url)
const storageKey = computed(() => `generation:${props.domain}:${props.sourceId}`)
let timer: ReturnType<typeof setTimeout> | undefined
let epoch = 0
watch(() => [props.visible, props.domain, props.sourceId, props.initialTaskId] as const, async ([visible]) => {
  clearTimeout(timer)
  const currentEpoch = ++epoch
  if (!visible) return
  error.value = ''
  if (!task.value && !prompt.value && props.initialPrompt) prompt.value = props.initialPrompt
  try {
    const loadedModels = await listResources('/system/model-configs', { pageSize: 100 })
    const loadedNodes = await listAgentNodes({ pageSize: 100 })
    if (currentEpoch !== epoch) return
    models.value = loadedModels.items.filter(m => m.status === 'active')
    nodes.value = loadedNodes.items.filter(n => n.status === 'active' && ['online', 'busy'].includes(n.data.agent_status || '') && n.data.capabilities?.includes('web_replay') && Date.now() - Date.parse(n.data.last_seen_at || '') < 90_000)
    const id = props.initialTaskId || Number(sessionStorage.getItem(storageKey.value))
    if (id !== task.value?.id) { task.value = null; candidate.value = null; editorValid.value = true }
    if (id && currentEpoch === epoch) await refresh(id)
  } catch (e) { if (currentEpoch === epoch) error.value = e instanceof Error ? e.message : '加载配置失败' }
}, { immediate: true })
async function refresh(id: number, restore = false) {
  const currentEpoch = epoch
  const result = await getGeneration(id)
  if (currentEpoch !== epoch) return
  if (result.data.domain !== props.domain || Number(result.data.source_id) !== props.sourceId) throw new Error('生成任务不属于当前功能')
  const executionTask = props.domain === 'WEB' && result.data.agent_task_id ? await getAgentTask(Number(result.data.agent_task_id)) : null
  if (currentEpoch !== epoch) return
  task.value = result
  agentTask.value = executionTask
  sessionStorage.setItem(storageKey.value, String(result.id))
  if ((restore || !candidate.value) && result.data.result?.candidate) candidate.value = result.data.result.candidate
  if (props.visible && (['queued', 'running'].includes(result.status) || verifying.value)) timer = setTimeout(() => refresh(id).catch(e => { error.value = String(e) }), 2000)
}
async function generate() {
  if (busy.value || verifying.value || !prompt.value.trim()) return
  const currentEpoch = epoch, conversationKey = storageKey.value
  error.value = ''
  if (mode.value === 'screenshots' && (!screenshots.value.length || screenshots.value.some(s => !s.description.trim()))) { error.value = '请上传截图并填写每张截图的操作描述'; return }
  saving.value = true
  try {
    const result = await submitGeneration(props.domain, { source_id: props.sourceId, prompt: prompt.value, model_id: modelId.value, include_knowledge: includeKnowledge.value, screenshots: mode.value === 'screenshots' ? screenshots.value : [], parent_task_id:task.value?.id || null, previous_candidate:task.value ? candidate.value : null })
    sessionStorage.setItem(conversationKey, String(result.task_id))
    if (currentEpoch !== epoch) return
    prompt.value = ''
    screenshots.value = []
    mode.value = 'text'
    candidate.value = null
    task.value = null
    editorValid.value = true
    await refresh(result.task_id)
  } catch (e) { if (currentEpoch === epoch) error.value = e instanceof Error ? e.message : '生成失败' } finally { saving.value = false }
}
async function perform(action: string, data: Record<string, unknown>) {
  if (!task.value) return
  saving.value = true
  error.value = ''
  try { await generationAction(task.value.id, action, data); clearTimeout(timer); await refresh(task.value.id); return true }
  catch (e) { error.value = e instanceof Error ? e.message : '操作失败' }
  finally { saving.value = false }
}
function verify() { return perform('verify', { candidate: candidate.value, node_key: nodeKey.value, wait_for_login: waitLogin.value, approve_side_effects: approveEffects.value }) }
function control(action: string) { return perform('control', { action }) }
async function accept() { if (await perform('accept', { candidate: candidate.value })) emit('saved') }
async function repair() {
  if (!task.value) return
  saving.value = true
  error.value = ''
  try {
    const r = await generationAction(task.value.id, 'repair', {})
    candidate.value = null
    task.value = null
    sessionStorage.setItem(storageKey.value, String(r.task_id))
    clearTimeout(timer)
    await refresh(r.task_id)
  } catch (e) { error.value = String(e) } finally { saving.value = false }
}
async function exportScript() {
  if (!task.value) return
  try {
    const file = await generationScript(task.value.id)
    downloadBundle(file)
  } catch (e) { error.value = String(e) }
}
onBeforeUnmount(() => { ++epoch; clearTimeout(timer) })
function newConversation() { if (candidate.value && !saved.value && !window.confirm('当前候选尚未保存，开始新对话？')) return; ++epoch; clearTimeout(timer); task.value = null; candidate.value = null; agentTask.value = null; prompt.value = ''; screenshots.value = []; error.value = ''; sessionStorage.removeItem(storageKey.value) }
</script>
<style scoped>
.generation-backdrop { position: fixed; inset: 0; background: #0006; z-index: 1200; display: flex; justify-content:center; align-items:center; padding:16px; }
.generation-drawer { width:min(1120px,100%); height:calc(100dvh - 32px); display:flex; flex-direction:column; background:#fff; box-shadow:0 8px 28px #0002; border-radius:6px; overflow:hidden; }
.generation-drawer.expanded { width:100%; height:100%; }
.conversation-workspace { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); flex:1; min-height:0; }
.conversation-pane { padding:20px; display:flex; flex-direction:column; min-width:0; min-height:0; border-right:1px solid #e3e8ed; }
.mobile-tabs { display:none; } .attachments { max-height:160px; overflow:auto; flex-shrink:0; }
.conversation-pane>label { display:grid; gap:6px; margin:8px 0; font-size:13px; } .conversation-pane>.check { display:flex; align-items:center; gap:8px; }
header, footer { display: flex; align-items: center; gap: 10px; padding: 16px 20px; flex-shrink: 0; border-bottom: 1px solid #e3e8ed; }
header h3 { margin: 0; font-size: 18px; flex: 1; } header button { width: 32px; height: 32px; padding: 6px; }
main { padding: 20px; overflow: auto; min-height: 0; min-width:0; } main > label, .verification > label { display: grid; gap: 6px; margin: 12px 0; }
textarea, select { width: 100%; min-width: 0; } .scope { margin-top: 0; font-weight: 600; overflow-wrap: anywhere; }
.modes, .task-state { display: flex; gap: 14px; align-items: center; flex-wrap: wrap; } .modes input, .check input { width: 16px; }
main .check, .verification .check { display: flex; align-items: center; gap: 8px; } .error { color: #b42318; } .warnings { color: #865b00; }
.task-state { background: #eef8f7; padding: 10px; font-size: 12px; margin: 16px 0; } .verification { border-top: 1px solid #e3e8ed; margin-top: 16px; padding-top: 4px; }
.verification img { width: 120px; height: 90px; object-fit: contain; margin: 6px; border: 1px solid #dce3eb; } video { display: block; width: 100%; max-height: 320px; }
footer { justify-content: flex-end; border-top: 1px solid #e3e8ed; border-bottom: 0; flex-wrap: wrap; } footer button { min-height: 36px; }
@media(max-width: 760px) { .generation-backdrop { padding:0; } .generation-drawer { height:100dvh; border-radius:0; } .conversation-workspace { grid-template-columns:minmax(0,1fr); } .conversation-pane { border-right:0; padding:12px; } .mobile-tabs { display:flex; gap:0; padding:0 12px; border-bottom:1px solid #e3e8ed; } .mobile-tabs button { border:0; border-radius:0; padding:9px 14px; } .mobile-tabs .active { border-bottom:2px solid #087f8c; color:#087f8c; } .mobile-hidden { display:none; } header, main, footer { padding:12px; } }
</style>
