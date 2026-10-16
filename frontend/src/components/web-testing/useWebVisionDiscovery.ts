import { computed, onBeforeUnmount, ref } from 'vue'
import { getErrorMessage } from '../../utils/error-message'
import { getAgentTask } from '../../services/agent.service'
import { cancelWebVision, confirmWebVisionLogin, getWebVisionTask, submitWebVision } from '../../services/web-vision.service'
import type { ResourceItem } from '../../types/resource'
import type { WebVisionRequest, WebVisionSubmission } from '../../types/web-vision'

export function useWebVisionDiscovery(completed: () => void) {
  const submission = ref<WebVisionSubmission | null>(null)
  const task = ref<ResourceItem | null>(null)
  const submitting = ref(false)
  const confirming = ref(false)
  const error = ref('')
  const active = computed(() => Boolean(submission.value) && (!task.value || ['pending', 'queued', 'running'].includes(task.value.status)))
  const waiting = computed(() => task.value?.status === 'running' && task.value.data.vision_phase === 'waiting_login')
  const progress = computed(() => String(task.value?.data.progress || submission.value?.message || ''))
  const calls = computed(() => Number(task.value?.data.model_http_calls || (task.value?.data.result as Record<string, unknown> | undefined)?.model_http_calls || 0))
  let timer: ReturnType<typeof setTimeout> | undefined
  let generation = 0

  function stop() { generation++; if (timer) clearTimeout(timer) }
  function reset() { stop(); submission.value = null; task.value = null; error.value = '' }

  async function poll(version: number) {
    const current = submission.value
    if (!current) return
    try {
      const response = current.agent_task_id ? await getAgentTask(current.agent_task_id) : await getWebVisionTask(current.task_id)
      if (generation !== version) return
      task.value = response
      if (['pending', 'queued', 'running'].includes(response.status)) {
        timer = setTimeout(() => void poll(version), 2000)
      } else if (response.status === 'canceled') {
        error.value = ''
      } else if (response.status === 'failed') {
        const result = response.data.result as Record<string, unknown> | undefined
        error.value = String(response.data.error || result?.error || '发现任务执行失败')
      } else {
        const result = response.data.result as Record<string, unknown> | undefined
        const issues = result?.feature_errors as { feature?: string; error?: string }[] | undefined
        if (issues?.length) error.value = issues.map(issue => `${issue.feature || ''}：${issue.error || '功能分析失败'}`).join('；')
        completed()
      }
    } catch (exception) {
      if (generation !== version) return
      error.value = getErrorMessage(exception)
      timer = setTimeout(() => void poll(version), 5000)
    }
  }

  function resume(value?: WebVisionSubmission | null) {
    stop()
    if (value) submission.value = value
    if (submission.value) void poll(generation)
  }

  async function start(payload: WebVisionRequest) {
    if (submitting.value || active.value) return
    reset()
    const version = generation
    submitting.value = true
    try {
      const response = await submitWebVision(payload)
      if (generation !== version) return
      submission.value = response
      resume()
    } catch (exception) { if (generation === version) error.value = getErrorMessage(exception) }
    finally { submitting.value = false }
  }

  async function confirm(action: 'continue' | 'cancel') {
    if (!submission.value || confirming.value || (action === 'continue' && !submission.value.agent_task_id)) return
    confirming.value = true
    error.value = ''
    try {
      if (action === 'cancel') await cancelWebVision(submission.value.task_id)
      else await confirmWebVisionLogin(submission.value.agent_task_id!, action)
      resume()
    }
    catch (exception) { error.value = getErrorMessage(exception) }
    finally { confirming.value = false }
  }

  onBeforeUnmount(stop)
  return { submission, task, submitting, confirming, error, active, waiting, progress, calls, start, resume, stop, reset, confirm }
}
