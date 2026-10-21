import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { getWebExecutionSummaries } from '../services/web-feature.service'
import type { WebExecutionScope, WebExecutionSummary } from '../types/web-execution'
import { useLatestRequest } from './useLatestRequest'

export function useWebExecutionSummaries(options: {
  projectId: () => number
  ids: () => number[]
  scope: WebExecutionScope
}) {
  const results = ref<Record<number, WebExecutionSummary>>({})
  const selectedRecordId = ref<number | null>(null)
  const { loading, error, run, cancel } = useLatestRequest('执行结果加载失败')
  let refreshedAt = 0

  function refresh() {
    const projectId = options.projectId()
    const ids = [...new Set(options.ids())]
    results.value = {}
    if (!projectId || !ids.length) { cancel(); return Promise.resolve() }
    refreshedAt = Date.now()
    return run(signal => getWebExecutionSummaries(projectId, options.scope, ids, signal), response => {
      results.value = Object.fromEntries(response.items.map(item => [item.id, item]))
    })
  }

  function onFocus() {
    if (document.visibilityState === 'visible' && Date.now() - refreshedAt > 1000) void refresh()
  }

  watch(() => [options.projectId(), ...options.ids()], () => void refresh(), { immediate: true })
  onMounted(() => window.addEventListener('focus', onFocus))
  onBeforeUnmount(() => window.removeEventListener('focus', onFocus))
  return { results, loading, error, refresh, selectedRecordId }
}
