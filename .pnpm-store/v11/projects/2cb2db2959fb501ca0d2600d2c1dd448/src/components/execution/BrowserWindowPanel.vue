<template>
  <section class="browser-window-panel" aria-label="任务浏览器">
    <div class="window-heading"><Monitor :size="16" /><strong>任务浏览器 #{{ taskId }}</strong></div>
    <dl v-if="info"><dt>执行电脑</dt><dd>{{ info.node_name || info.node_key || '未分配' }}</dd><dt>浏览器</dt><dd>{{ info.window.browser_name || (info.headed ? '启动中' : '服务器无头') }}</dd></dl>
    <p v-if="info?.window.label" class="window-label">{{ info.window.label }}</p>
    <div class="window-actions"><span role="status">{{ status }}</span><button type="button" title="恢复并激活当前任务浏览器" :disabled="!info?.can_show || showing" @click="show"><MonitorUp :size="16" />{{ showing ? '等待激活确认' : '显示浏览器' }}</button></div>
    <p v-if="error" class="window-error" role="alert">{{ error }}</p>
  </section>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { Monitor, MonitorUp } from 'lucide-vue-next'
import { getBrowserWindow, showBrowserWindow } from '../../services/browser-window.service'
import type { BrowserWindowInfo } from '../../types/browser-window'
import { getErrorMessage } from '../../utils/error-message'
const props = defineProps<{ taskId: number }>()
const info = ref<BrowserWindowInfo | null>(null), error = ref(''), showing = ref(false), feedback = ref('')
let timer: ReturnType<typeof setTimeout> | undefined
let epoch = 0, requestedAt = 0, commandId = ''
const status = computed(() => {
  if (!info.value) return '读取窗口状态中'
  const i = info.value
  if (!i.headed) return '无本地有头窗口'
  if (['success', 'failed', 'canceled'].includes(i.task_status)) return '任务已结束，窗口已关闭'
  if (i.window.status === 'closed') return '任务窗口已关闭'
  if (!i.online && i.node_key) return '执行节点已离线'
  if (!i.supported) return 'Agent 需要升级窗口控制能力'
  if (feedback.value) return feedback.value
  if (i.window.status === 'unavailable') return '无法精确识别任务窗口'
  if (i.window.status !== 'open') return '等待 Agent 启动任务窗口'
  if (!i.can_show) return '窗口状态更新中'
  if (i.window.focus === 'blocked') return '系统未允许自动激活，任务栏已提醒'
  return ({ waiting_login: '等待人工登录', waiting_input: '等待人工输入', recording: '操作录制中', analyzing: 'AI 分析中', running: '执行中' } as Record<string, string>)[i.window.phase || ''] || '任务窗口已打开'
})
watch(() => props.taskId, () => { ++epoch; clearTimeout(timer); info.value = null; error.value = ''; feedback.value = ''; showing.value = false; commandId = ''; void poll(epoch) }, { immediate: true })
async function poll(version: number) {
  try {
    const result = await getBrowserWindow(props.taskId)
    if (version !== epoch) return
    info.value = result
    error.value = ''
    if (showing.value && commandId && result.command.id === commandId && result.command.status !== 'pending') {
      const messages: Record<string, string> = { active: '已显示当前任务浏览器', blocked: '系统未允许激活，任务栏已提醒', failed: '窗口激活失败', closed: '任务窗口已关闭', expired: '激活请求已超时' }
      feedback.value = messages[result.command.status || ''] || '未收到窗口激活确认'
      showing.value = false
    }
    if (showing.value && Date.now() - requestedAt > 15_000) { showing.value = false; feedback.value = '请求超时，未收到 Agent 激活确认' }
    if (!['success', 'failed', 'canceled'].includes(result.task_status)) timer = setTimeout(() => void poll(version), showing.value ? 1000 : 2000)
  } catch (e) {
    if (version !== epoch) return
    error.value = getErrorMessage(e)
    if (showing.value && Date.now() - requestedAt > 15_000) { showing.value = false; feedback.value = '未收到 Agent 激活确认' }
    timer = setTimeout(() => void poll(version), 4000)
  }
}
async function show() {
  const version = epoch
  showing.value = true; requestedAt = Date.now(); feedback.value = '正在请求显示任务窗口'; error.value = ''; commandId = ''
  try {
    const result = await showBrowserWindow(props.taskId)
    if (version !== epoch) return
    commandId = result.command_id
    clearTimeout(timer)
    await poll(version)
  } catch (e) { if (version === epoch) { error.value = getErrorMessage(e); showing.value = false; feedback.value = '' } }
}
onBeforeUnmount(() => { ++epoch; clearTimeout(timer) })
</script>
<style scoped>
.browser-window-panel { border-top: 1px solid #e2e8ee; padding: 12px 0; margin-top: 10px; min-width: 0; }
.window-heading, .window-actions, .window-actions button { display: flex; align-items: center; gap: 8px; }
.window-heading { font-size: 13px; }.window-heading svg, button svg { flex-shrink: 0; }
dl { display: grid; grid-template-columns: 70px minmax(0, 1fr); gap: 5px 10px; margin: 10px 0; font-size: 12px; }dt { color: #66717f; }dd { margin: 0; overflow-wrap: anywhere; }
.window-label { font-size: 12px; font-weight: 600; overflow-wrap: anywhere; }
.window-actions { justify-content: space-between; flex-wrap: wrap; font-size: 12px; }.window-actions span { overflow-wrap: anywhere; }.window-actions button { min-height: 34px; white-space: nowrap; }
.window-error { color: #b42318; font-size: 12px; overflow-wrap: anywhere; }
</style>
