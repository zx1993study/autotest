<template>
  <div class="app-live">
    <div class="live-workspace"><section class="chat-pane">
      <div class="scope-controls"><label>设备<select v-model.number="deviceId" :disabled="!!task"><option :value="null">选择设备</option><option v-for="device in devices" :key="device.id" :value="device.id">{{ device.name }}</option></select></label><label>应用<select v-model.number="entryId" :disabled="!!task"><option :value="null">选择应用</option><option v-for="entry in entries" :key="entry.id" :value="entry.id">{{ entry.name }}</option></select></label></div>
      <template v-if="!task"><label>模型<select v-model.number="modelId"><option :value="null">当前模型</option><option v-for="model in models" :key="model.id" :value="model.id">{{ model.name }}</option></select></label><label class="check"><input v-model="currentScreen" type="checkbox" />从当前界面继续</label><label class="check"><input v-model="recordVideo" type="checkbox" />记录操作视频</label><label class="check"><input v-model="approveEffects" type="checkbox" />允许在所选应用执行本次描述的操作</label></template>
      <GenerationConversation v-model="prompt" :messages="task?.live.conversation || []" :busy="busy || active && !canSend" :disabled="!canSend" :progress="task ? phaseLabel : ''" :error="error" @send="send" />
    </section><section class="result-pane"><AppExplorationEvidence :task="task" :label="phaseLabel" /><label v-if="task && task.live.steps.length" class="scene-name">场景名称<input v-model="name" aria-label="场景名称" maxlength="160" :disabled="!!task.saved_resource" /></label></section></div>
    <footer>
      <button v-if="task && active" type="button" title="停止任务" :disabled="busy" @click="control('cancel')"><Square :size="15" />停止</button>
      <button v-if="task && active && ['connecting','observing','planning','ready','executing'].includes(task.live.phase)" type="button" :disabled="busy" @click="control('pause')"><Pause :size="15" />暂停</button>
      <button v-if="task && active && ['waiting_app','waiting_app_confirmation'].includes(task.live.phase)" type="button" :disabled="busy" @click="control('check_app')"><RefreshCw :size="15" />重新检测应用</button>
      <button v-if="task?.live.phase === 'waiting_app_confirmation' && active" type="button" :disabled="busy" @click="confirmApp"><Check :size="15" />确认绑定当前应用</button>
      <button v-if="task?.live.phase === 'paused' && active && !task.live.outcome_unknown" type="button" :disabled="busy" @click="control('resume')"><Play :size="15" />继续</button>
      <button v-if="task?.live.outcome_unknown && active" type="button" :disabled="busy" @click="confirmNotExecuted">确认未生效，重新观察</button>
      <button v-if="task?.live.phase === 'waiting_manual' && active" type="button" :disabled="busy" @click="control('manual_done')">人工操作完成，继续</button>
      <button v-if="task?.live.phase === 'waiting_approval' && active" type="button" :disabled="busy" @click="approve">确认本次操作</button>
      <button v-if="task && active && task.live.phase !== 'executing'" type="button" :disabled="busy" @click="control('finish')">结束任务</button>
      <button v-if="task?.live.phase === 'waiting_next' && active" type="button" :disabled="busy || !task.live.steps.length || !name.trim()" @click="save"><Save :size="15" />保存场景</button>
      <button v-if="task?.saved_resource" type="button" @click="openScenario">场景详情</button>
      <button v-if="task && !active" type="button" @click="newTask"><MessageSquarePlus :size="15" />新任务</button>
    </footer>
  </div>
</template>
<script setup lang="ts">
import { computed,onBeforeUnmount,onMounted,ref } from 'vue'
import { useRouter } from 'vue-router'
import { Square,Pause,Play,Save,MessageSquarePlus,RefreshCw,Check } from 'lucide-vue-next'
import type { AppFeature } from '../../types/app-feature'
import type { ResourceItem,SelectOptionRecord } from '../../types/resource'
import type { AppExploration } from '../../types/app-exploration'
import { listResources } from '../../api/http'
import { listDeviceOptions } from '../../services/app-feature.service'
import { startAppExploration,activeAppExploration,getAppExploration,controlAppExploration,acceptAppExploration } from '../../services/app-exploration.service'
import { getErrorMessage as detailError } from '../../utils/error-message'
import GenerationConversation from '../generation/GenerationConversation.vue'
import AppExplorationEvidence from './AppExplorationEvidence.vue'
const props = defineProps<{feature:AppFeature}>()
const emit = defineEmits<{saved:[];active:[value:boolean]}>()
const router = useRouter()
const devices = ref<SelectOptionRecord[]>([]),entries = ref<ResourceItem[]>([]),models = ref<ResourceItem[]>([])
const deviceId = ref<number|null>(Number(props.feature.data?.default_device_id)||null)
const entryId = ref<number|null>(Number(props.feature.data?.default_entry_id)||null),modelId = ref<number|null>(null)
const approveEffects = ref(false),currentScreen = ref(false),recordVideo = ref(true)
const prompt = ref(''),name = ref(props.feature.name),error = ref(''),busy = ref(false)
const task = ref<AppExploration|null>(null)
const active = computed(() => !!task.value && ['pending','running'].includes(task.value.status))
const phases:Record<string,string> = {connecting:'连接设备并识别应用',waiting_app:'等待打开目标应用',waiting_app_confirmation:'等待确认应用身份',observing:'采集设备界面',planning:'AI 分析下一步',ready:'等待执行',executing:'设备操作中',waiting_next:'本轮完成，可补充下一步',waiting_user:'等待补充',waiting_manual:'等待人工操作',waiting_approval:'等待操作确认',paused:'已暂停',saving:'保存场景中',finishing:'任务结束中',canceled:'已中止'}
const phaseLabel = computed(() => !task.value ? '尚未连接设备' : active.value ? phases[task.value.live.phase] || task.value.live.phase : ({success:'任务已完成',failed:'任务中断',canceled:'任务已中止'} as Record<string,string>)[task.value.status] || task.value.status)
const canSend = computed(() => !task.value || active.value && ['waiting_next','waiting_user','paused'].includes(task.value.live.phase) && !task.value.live.outcome_unknown)
const key = `app-live:${props.feature.id}`
let timer:ReturnType<typeof setTimeout>|undefined,disposed = false
function update(value:AppExploration|null) { if(disposed) return; task.value=value; emit('active',active.value); if(value) { sessionStorage.setItem(key,String(value.id)); deviceId.value=value.device_id;entryId.value=value.entry_id } }
async function refresh() { clearTimeout(timer); if(!task.value || disposed) return; try { update(await getAppExploration(props.feature.id,task.value.id)) } finally { if(active.value && !disposed) timer=setTimeout(() => refresh().catch(e => { error.value=detailError(e) }),1500) } }
onMounted(async () => { try {
  devices.value=await listDeviceOptions(props.feature.project_id)
  entries.value=(await listResources('/app-testing/entries',{project_id:props.feature.project_id,pageSize:100})).items.filter(e => e.status === 'active')
  models.value=(await listResources('/system/model-configs',{pageSize:100})).items.filter(m => m.status === 'active' && m.data.supports_vision)
  const existing=await activeAppExploration(props.feature.id)
  const id=Number(sessionStorage.getItem(key))
  update(existing || (id ? await getAppExploration(props.feature.id,id) : null))
  if(active.value) await refresh()
} catch(e) { error.value=detailError(e) } })
async function send() { if(busy.value || !canSend.value || !prompt.value.trim()) return; busy.value=true;error.value='';clearTimeout(timer);try {
  if(!task.value) { if(!deviceId.value) throw new Error('请选择设备'); if(!entryId.value) throw new Error('请选择应用'); if(!approveEffects.value) throw new Error('请确认允许在所选应用执行本次描述的操作'); update(await startAppExploration(props.feature.id,{device_id:deviceId.value,entry_id:entryId.value,prompt:prompt.value,request_id:crypto.randomUUID(),model_id:modelId.value,approve_effects:approveEffects.value,start_from_current_screen:currentScreen.value,record_video:recordVideo.value})) }
  else update(await controlAppExploration(props.feature.id,task.value.id,{action:'message',message:prompt.value,request_id:crypto.randomUUID()}))
  prompt.value='';await refresh()
} catch(e) { error.value=detailError(e) } finally { busy.value=false } }
async function control(action:string) { if(!task.value || busy.value) return;busy.value=true;error.value='';clearTimeout(timer);try { update(await controlAppExploration(props.feature.id,task.value.id,{action,nonce:task.value.live.nonce || '',request_id:crypto.randomUUID()}));await refresh() } catch(e) { error.value=detailError(e) } finally { busy.value=false } }
function approve() { if(window.confirm(`确认执行：${task.value?.live.command?.step.name || '本次操作'}？`)) void control('approve') }
function confirmApp() { const candidate=task.value?.live.app_candidate; if(candidate && window.confirm(`确认手机当前打开的是“${entries.value.find(e => e.id === entryId.value)?.name || '所选应用'}”，并保存 ${candidate.bundle_id}？`)) void control('confirm_app') }
function confirmNotExecuted() { if(window.confirm('仅当已在手机确认上一动作没有生效时继续。确定重新观察？')) void control('confirm_not_executed') }
async function save() { if(!task.value || busy.value) return;busy.value=true;error.value='';clearTimeout(timer);try { await acceptAppExploration(props.feature.id,task.value.id,name.value);emit('saved');await refresh() } catch(e) { error.value=detailError(e) } finally { busy.value=false } }
function openScenario() { if(task.value?.saved_resource) void router.push(`/app/features/${props.feature.id}/scenarios/${task.value.saved_resource.id}`) }
function newTask() { clearTimeout(timer);update(null);sessionStorage.removeItem(key);error.value='';prompt.value='' }
onBeforeUnmount(() => { disposed=true;clearTimeout(timer) })
</script>
<style scoped>
.app-live { display:flex; flex-direction:column; flex:1; min-height:0; } .live-workspace { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); flex:1; min-height:0; }
.chat-pane { display:flex; flex-direction:column; padding:18px; min-height:0; min-width:0; border-right:1px solid #e3e8ed; } .scope-controls { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; } label { display:grid; gap:6px; font-size:13px; min-width:0; margin:0 0 12px; } .check { display:flex; align-items:center; gap:8px; } .check input { width:16px; } select,input { min-width:0; width:100%; }
.result-pane { overflow:auto; padding:18px; min-height:0; min-width:0; } .scene-name { margin-top:16px; } footer { display:flex; flex-wrap:wrap; gap:8px; justify-content:flex-end; padding:12px 18px; border-top:1px solid #e3e8ed; flex-shrink:0; } footer button { display:flex; align-items:center; gap:6px; min-height:36px; }
@media(max-width:760px) { .live-workspace { display:flex; flex-direction:column; overflow:auto; } .chat-pane { min-height:480px; flex-shrink:0; border-right:0; } .result-pane { overflow:visible; } .scope-controls { grid-template-columns:1fr; } }
</style>
