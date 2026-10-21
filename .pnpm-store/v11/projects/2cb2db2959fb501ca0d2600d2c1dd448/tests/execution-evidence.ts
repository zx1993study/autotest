import { createApp, defineComponent, h, ref } from 'vue'
import ExecutionRecordDetailDialog from '../src/components/reports/ExecutionRecordDetailDialog.vue'
import ApiCaseDetailContent from '../src/components/resource/ApiCaseDetailContent.vue'
import type { ResourceItem } from '../src/types/resource'
import { evidenceText, executionEvidence } from '../src/utils/executionEvidence'
import { redactEvidence } from '../src/utils/evidencePrivacy'
import '../src/styles.css'

const record = (data: Record<string, unknown>, status = 'success') => ({
  id: 4, name: 'Historical record', status, data, created_at: '', updated_at: ''
})
const checks: string[] = []
function check(name: string, value: unknown) {
  if (!value) throw new Error(name)
  checks.push(name)
}
const result = executionEvidence(record({ case_type: 'API', response_status: 200,
  response_body: '{"code":500,"msg":"库存不足"}', assertions: [{ passed: false, actual: 500, expected: 200 }] }, 'failed'))
check('HTTP 200 does not change failed assertion', result.assertions[0].outcome === 'failed' && result.httpStatus === 200)
check('Business code independent of HTTP status', result.businessCode === 500)
check('Expected business rejection can pass', executionEvidence(record({ response_status: 200, response_body: '{"code":500}',
  assertions: [{ expected: 500, actual: 500, passed: true }] })).assertions[0].outcome === 'passed')
check('Runtime assertion pass survives failed record', executionEvidence(record({ assertions: [{ passed: true }] }, 'failed')).assertions[0].outcome === 'passed')
check('Configured assertions unknown', executionEvidence(null, { assertions: [{ type: 'status', expected: 200 }] }).assertions[0].outcome === 'unknown')
check('String passed never inferred', executionEvidence(record({ assertions: [{ passed: 'true' }] })).assertions[0].outcome === 'unknown')
check('Explicit empty runtime assertions not replaced', executionEvidence(record({ assertions: [] }), { assertions: [{ expected: 200 }] }).assertions.length === 0)
check('Web definitions never inferred from record success', executionEvidence(record({ case_type: 'WEB', assertions: [{ type: 'text' }] })).assertions[0].outcome === 'unknown')
check('Missing response not fabricated', executionEvidence(record({ case_type: 'API' })).response == null)
check('Current case definition never replaces missing historical request', executionEvidence(record({ case_type: 'API' }), {
  request: { body: { name: 'Current definition' } }
}).request == null)
check('Plain response kept', evidenceText(executionEvidence(record({ response_body: 'upstream unavailable' })).response).includes('upstream unavailable'))
check('JSON null body preserved', evidenceText(executionEvidence(record({ response_body: 'null' })).response).includes('"body": null'))
check('Double encoded JSON parsed', executionEvidence(record({ response_body: JSON.stringify('{"code":201}') })).businessCode === 201)
const secret = {
  request: { headers: { Authorization: 'Bearer hidden-header', COOKIE: 'hidden-cookie' },
    url: 'https://hidden-user:hidden-pass@example.test/path?access_token=hidden-query&q=normal',
    body: JSON.stringify({ password: 'hidden-body', nested: { apiKey: 'hidden-key' } }) },
  response_body: JSON.stringify({ token: 'hidden-response', rows: [{ name: 'Visible customer' }] }),
  storage_state: { cookies: [{ value: 'hidden-state' }] },
  steps: [{ selector: 'input[type=password]', value: 'hidden-step' }],
  assertion: { path: '$.password', expected: 'hidden-expected', actual: 'hidden-actual' }
}
const original = JSON.stringify(secret)
const safe = evidenceText(secret)
check('All structured secrets masked including encoded JSON and URL', !safe.includes('hidden-') && safe.includes('Visible customer') && safe.includes('normal'))
check('Redaction never mutates source evidence', JSON.stringify(secret) === original)
check('Truncated JSON still masks password', !evidenceText('{"password":"hidden-truncated').includes('hidden-truncated'))
check('Plain authorization masked', !evidenceText('Authorization: Bearer hidden-plain').includes('hidden-plain'))
check('Redaction idempotent', evidenceText(redactEvidence(secret)) === safe)

const selected = ref<number | null>(null)
const caseItem = ref<ResourceItem | null>(null)
const showExecution = ref(true)
Object.assign(window, {
  evidenceChecks: checks,
  openEvidence: (id: number | null) => { selected.value = id },
  showCaseEvidence: (item: ResourceItem | null, execution = true) => { caseItem.value = item; showExecution.value = execution }
})
createApp(defineComponent({ setup: () => () => h('main', [
  h('p', `${checks.length} evidence checks passed`),
  selected.value != null ? h(ExecutionRecordDetailDialog, { recordId: selected.value, onClose: () => { selected.value = null } }) : null,
  caseItem.value ? h(ApiCaseDetailContent, { item: caseItem.value, showExecution: showExecution.value }) : null
]) })).mount('#app')
