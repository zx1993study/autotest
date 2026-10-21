import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { createSourceRun, getSourceRun, importSourceCatalog, listSourceCases, listSourceRuns } from '../services/miniapp-source.service'
import type { SourceCase, SourceRun } from '../types/miniapp-source'

export function useMiniappSource() {
  const projectId = ref(0)
  const ready = ref(false)
  const cases = ref<SourceCase[]>([])
  const runs = ref<SourceRun[]>([])
  const selected = ref<number[]>([])
  const category = ref('')
  const keyword = ref('')
  const platform = ref('mp-weixin')
  const busy = ref(false)
  const error = ref('')
  const message = ref('')
  const detail = ref<SourceCase | null>(null)
  const runDetail = ref<SourceRun | null>(null)
  const page = ref(1)
  let version = 0
  let runRequest = 0
  let timer: ReturnType<typeof setTimeout> | undefined
  let disposed = false
  const filtered = computed(() => cases.value.filter(row => (!category.value || row.data.category === category.value)
    && (!keyword.value || `${row.id} ${row.name} ${row.data.definition?.id}`.toLowerCase().includes(keyword.value.toLowerCase()))))
  const visible = computed(() => filtered.value.slice((page.value - 1) * 50, page.value * 50))
  const pages = computed(() => Math.max(1, Math.ceil(filtered.value.length / 50)))

  function schedule() {
    clearTimeout(timer)
    if (!disposed && runs.value.some(run => ['queued', 'running'].includes(run.status))) {
      timer = setTimeout(() => void refreshRuns(), 2000)
    }
  }

  async function refreshRuns() {
    const current = version
    try {
      const rows = await listSourceRuns(projectId.value)
      if (current !== version || disposed) return
      runs.value = rows
      if (runDetail.value && rows.some(row => row.id === runDetail.value?.id)) {
        const id = runDetail.value.id
        const result = await getSourceRun(id)
        if (current === version && !disposed && runDetail.value?.id === id) runDetail.value = result
      }
      schedule()
    } catch (cause) { if (current === version) error.value = String(cause) }
  }

  async function load() {
    const current = ++version
    runRequest++
    clearTimeout(timer)
    selected.value = []; cases.value = []; runs.value = []; detail.value = null; runDetail.value = null
    if (!ready.value || !projectId.value) return
    busy.value = true; error.value = ''; message.value = ''
    try {
      const rows = await listSourceCases(projectId.value)
      if (current !== version || disposed) return
      cases.value = rows
      await refreshRuns()
    } catch (cause) { if (current === version) error.value = String(cause) }
    finally { if (current === version) busy.value = false }
  }

  async function importFile(file?: File) {
    if (!file || !projectId.value) return
    const current = version
    const project = projectId.value
    busy.value = true; error.value = ''
    try {
      if (file.size > 5 * 1024 * 1024) throw new Error('测试包不能超过 5 MB')
      const catalog = JSON.parse(await file.text())
      if (current !== version || disposed) return
      const result = await importSourceCatalog(project, catalog)
      if (current !== version || disposed) return
      await load()
      message.value = `新增 ${result.created_pages} 个页面、${result.created_cases} 个用例；跳过 ${result.skipped_cases} 个；冲突 ${result.conflicts.length} 个`
    } catch (cause) { if (current === version) error.value = String(cause) }
    finally { if (current === version) busy.value = false }
  }

  async function execute() {
    const current = version
    busy.value = true; error.value = ''
    try {
      const run = await createSourceRun(projectId.value, selected.value, platform.value)
      if (current !== version || disposed) return
      runDetail.value = run
      await refreshRuns()
    } catch (cause) { if (current === version) error.value = String(cause) }
    finally { if (current === version) busy.value = false }
  }

  async function showRun(id: number) {
    const current = version
    const request = ++runRequest
    try {
      const result = await getSourceRun(id)
      if (current === version && request === runRequest && !disposed) runDetail.value = result
    } catch (cause) { if (current === version) error.value = String(cause) }
  }

  function closeRun() { runRequest++; runDetail.value = null }

  watch([ready, projectId], () => void load())
  watch([category, keyword], () => { page.value = 1 })
  onBeforeUnmount(() => { disposed = true; version += 1; clearTimeout(timer) })
  return { projectId, ready, cases, runs, selected, category, keyword, platform, busy, error, message,
    detail, runDetail, page, pages, filtered, visible, load, importFile, execute, showRun, closeRun }
}
