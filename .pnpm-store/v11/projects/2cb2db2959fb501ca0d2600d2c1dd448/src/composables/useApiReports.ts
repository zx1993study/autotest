import { ref, watch } from 'vue'
import { listApiReports } from '../services/api-report.service'
import type { ApiReportRow } from '../types/api-report'
import { useLatestRequest } from './useLatestRequest'

export function useApiReports() {
  const projectId = ref(0)
  const ready = ref(false)
  const kind = ref<'' | 'api' | 'flow'>('')
  const status = ref('')
  const keyword = ref('')
  const appliedKeyword = ref('')
  const page = ref(1)
  const pageSize = ref(20)
  const total = ref(0)
  const rows = ref<ApiReportRow[]>([])
  const selected = ref<ApiReportRow | null>(null)
  const { loading, error, run, cancel } = useLatestRequest('加载 API 报告失败')

  function load() {
    if (!ready.value) return
    return run(signal => listApiReports({
      page: page.value, pageSize: pageSize.value,
      ...(projectId.value ? { project_id: projectId.value } : {}),
      ...(kind.value ? { kind: kind.value } : {}),
      ...(status.value ? { status: status.value } : {}),
      ...(appliedKeyword.value ? { keyword: appliedKeyword.value } : {})
    }, signal), result => { rows.value = result.items; total.value = result.total })
  }
  function search() {
    appliedKeyword.value = keyword.value.trim()
    page.value = 1
    void load()
  }
  function paginate(nextPage: number, nextSize: number) {
    page.value = nextPage
    pageSize.value = nextSize
    void load()
  }
  watch([projectId, kind, status, ready], () => {
    cancel()
    rows.value = []
    total.value = 0
    selected.value = null
    page.value = 1
    void load()
  })
  return { projectId, ready, kind, status, keyword, page, pageSize, total, rows, selected, loading, error, load, search, paginate }
}
