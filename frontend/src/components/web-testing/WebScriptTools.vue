<template>
  <div class="script-tools">
    <button type="button" :disabled="busy" @click="open"><Circle :size="15" />录制操作</button>
    <button type="button" title="导出脚本与输入文件" :disabled="busy || !versionId" @click="exportScript"><Download :size="15" />导出</button>
    <p v-if="exportError" class="error" role="alert">{{ exportError }}</p>
    <Teleport to="body">
      <div v-if="visible" class="modal-backdrop" @click.self="visible = false">
        <section class="modal-panel recording-panel" role="dialog" aria-modal="true" aria-labelledby="recording-title">
          <header><h3 id="recording-title">录制操作</h3><button type="button" title="关闭" aria-label="关闭" @click="visible = false"><X :size="18" /></button></header>
          <main>
            <template v-if="!active && !candidate">
              <label>本地节点<select v-model="nodeKey"><option value="">选择在线 Agent</option><option v-for="node in nodes" :key="node.id" :value="node.data.node_key">{{ node.name }}</option></select></label>
              <label class="check"><input v-model="approved" type="checkbox" />确认由我操作页面，包括填写、提交和删除</label>
            </template>
            <p v-if="task" role="status">录制任务 #{{ task.id }} · {{ states[task.status] || task.status }}</p>
            <BrowserWindowPanel v-if="task" :task-id="task.id" />
            <p v-if="task?.data.error" class="error">{{ task.data.error }}</p>
            <ul v-if="warnings.length"><li v-for="warning in warnings" :key="warning">{{ warning }}</li></ul>
            <GenerationCandidateEditor v-if="candidate" v-model="candidate" domain="WEB" @valid="valid = $event" />
            <div class="evidence"><a v-for="shot in shots" :key="shot.screenshot_url" :href="media(shot.screenshot_url)" target="_blank" rel="noopener noreferrer"><img :src="media(shot.screenshot_url)" alt="录制页面截图" /></a></div>
            <p v-if="error" class="error" role="alert">{{ error }}</p>
          </main>
          <footer>
            <button v-if="active" type="button" :disabled="busy" @click="control('cancel')"><Square :size="15" />取消录制</button>
            <button v-if="task?.status === 'running'" type="button" :disabled="busy" @click="control('stop')"><Square :size="15" />停止录制</button>
            <button v-if="!active" type="button" :disabled="busy || !nodeKey || !approved" @click="start"><Circle :size="15" />{{ task ? '重新录制' : '开始录制' }}</button>
            <button v-if="candidate && task?.status === 'success'" type="button" :disabled="busy || !valid || saved" @click="save"><Save :size="15" />{{ saved ? '已保存' : '保存为新版本' }}</button>
          </footer>
        </section>
      </div>
    </Teleport>
  </div>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { Circle, Download, Save, Square, X } from 'lucide-vue-next'
import { getAgentTask, listAgentNodes } from '../../services/agent.service'
import { exportWebScript, featureAction, webOperationControl } from '../../services/web-feature.service'
import { downloadBundle } from '../../utils/downloadBundle'
import { withScreenshotAccessToken as media } from '../../utils/screenshotUrl'
import type { AgentNode, AgentTask } from '../../types/agent'
import BrowserWindowPanel from '../execution/BrowserWindowPanel.vue'
import GenerationCandidateEditor from '../generation/GenerationCandidateEditor.vue'
const props = defineProps<{ featureId: number; versionId?: number }>()
const emit = defineEmits<{ saved: [] }>()
const visible = ref(false), busy = ref(false), error = ref(''), exportError = ref(''), nodeKey = ref(''), approved = ref(false), valid = ref(true), saved = ref(false)
const nodes = ref<AgentNode[]>([]), task = ref<AgentTask | null>(null), candidate = ref<Record<string,any> | null>(null)
const active = computed(() => ['pending', 'running'].includes(task.value?.status || ''))
const result = computed(() => (task.value?.data.result?.records?.[0] as any)?.data || {})
const warnings = computed<string[]>(() => result.value.warnings || [])
const shots = computed<any[]>(() => (result.value.screenshots || []).filter((s: any) => s.screenshot_url))
const states: Record<string,string> = { pending:'等待节点', running:'录制中', success:'待审阅', failed:'录制未完成', canceled:'已取消' }
const key = `web-recording:${props.featureId}`
let timer: ReturnType<typeof setTimeout> | undefined, epoch = 0
async function open() {
  visible.value = true; error.value = ''
  try {
    nodes.value = (await listAgentNodes({pageSize:100})).items.filter(n => n.status === 'active' && ['online','busy'].includes(n.data.agent_status) && n.data.capabilities?.includes('web_recording') && Date.now() - Date.parse(n.data.last_seen_at || '') < 90000)
    nodeKey.value ||= (nodes.value.find(n => n.data.default_local_headed) || nodes.value[0])?.data.node_key || ''
    const id = Number(sessionStorage.getItem(key)); if (id) { clearTimeout(timer); ++epoch; await poll(id) }
  } catch (e) { error.value = String(e) }
}
async function poll(id: number) {
  const current = epoch
  try {
    const next = await getAgentTask(id)
    if (current !== epoch) return
    if (!next.data.payload?.recording || next.data.payload.source_id !== props.featureId) throw new Error('录制任务不属于当前功能')
    task.value = next; saved.value = !!next.data.saved_version
    if (!candidate.value && result.value.candidate) candidate.value = result.value.candidate
    if (active.value) timer = setTimeout(() => void poll(id),1500)
  } catch (e) { error.value = String(e) }
}
async function start() {
  busy.value = true; error.value = ''; clearTimeout(timer); ++epoch
  try { const queued = await featureAction(props.featureId,'recording',{node_key:nodeKey.value,approve_side_effects:approved.value}); candidate.value = null; saved.value = false; sessionStorage.setItem(key,String(queued.agent_task_id)); await poll(queued.agent_task_id) }
  catch (e) { error.value = String(e) } finally { busy.value = false }
}
async function control(action: 'cancel' | 'stop') { if (!task.value) return; busy.value = true; error.value = ''; try { await webOperationControl(task.value.id,action) } catch(e) { error.value = String(e) } finally { busy.value = false } }
async function save() { if (!task.value || !candidate.value) return; busy.value = true; error.value = ''; try { await featureAction(props.featureId,'recording/accept',{task_id:task.value.id,candidate:candidate.value}); saved.value = true; emit('saved') } catch(e) { error.value = String(e) } finally { busy.value = false } }
async function exportScript() { busy.value = true; exportError.value = ''; try { downloadBundle(await exportWebScript(props.featureId,props.versionId)) } catch(e) { exportError.value = String(e) } finally { busy.value = false } }
onBeforeUnmount(() => { ++epoch; clearTimeout(timer) })
</script>
<style scoped>
.script-tools { display:flex; gap:8px; flex-wrap:wrap; } button { display:inline-flex; align-items:center; gap:6px; } .error { color:#b42318; overflow-wrap:anywhere; }
.recording-panel { width:min(760px,calc(100vw - 24px)); max-height:90dvh; display:flex; flex-direction:column; }
header,footer { display:flex; gap:10px; align-items:center; padding:16px; flex-wrap:wrap; } header h3 { margin:0; flex:1; } main { padding:0 16px 16px; overflow:auto; min-height:0; } main > label { display:grid; gap:8px; margin:12px 0; } main .check { display:flex; align-items:center; } .check input { width:16px; } select { width:100%; } footer { justify-content:flex-end; border-top:1px solid #e2e8f0; } .evidence { display:flex; gap:8px; flex-wrap:wrap; } .evidence img { width:160px; height:110px; object-fit:contain; border:1px solid #e2e8f0; }
</style>
