<template>
  <Teleport to="body"><div v-if="visible" class="modal-backdrop" @click.self="close"><section class="modal-panel feature-editor" role="dialog" aria-modal="true" aria-labelledby="feature-editor-title">
    <header class="modal-header"><h3 id="feature-editor-title">{{ feature ? '编辑功能' : '添加功能' }}</h3><button type="button" title="关闭" aria-label="关闭" @click="close"><X :size="18" /></button></header>
    <form @submit.prevent="save"><div class="editor-tabs" role="tablist"><button v-for="item in tabs" :key="item.key" type="button" role="tab" :aria-selected="tab === item.key" :class="{ active: tab === item.key }" @click="tab = item.key">{{ item.label }}</button></div>
      <main><div v-show="tab === 'basic'" class="form-grid"><label class="field full"><span>功能名称</span><input v-model.trim="form.name" required maxlength="128" /></label>
        <label class="field"><span>业务类型</span><select v-model="form.feature_type"><option v-for="(label, type) in types" :key="type" :value="type">{{ label }}</option></select></label>
        <label class="field"><span>状态</span><select v-model="form.status"><option value="active">启用</option><option value="disabled">停用</option></select></label>
        <label class="field full"><span>项目鉴权</span><select v-model="form.auth_id"><option :value="null">继承页面鉴权</option><option v-for="auth in auths" :key="auth.id" :value="auth.id">{{ auth.name }}</option></select></label>
        <label class="field full"><span>操作描述与预期结果</span><textarea v-model="form.description" rows="5" /></label></div>
        <WebParameterEditor v-show="tab === 'parameters'" v-model="form.parameters" @valid="parametersValid = $event" />
        <div v-show="tab === 'script'"><GenerationCandidateEditor v-if="form.candidate" v-model="form.candidate" domain="WEB" @valid="scriptValid = $event" /><p v-else class="empty">暂无操作脚本</p></div>
        <p v-if="error" class="error" role="alert">{{ error }}</p></main>
      <footer class="modal-actions"><button type="button" :disabled="saving" @click="close">取消</button><button type="submit" :disabled="saving || !scriptValid || !parametersValid">{{ saving ? '保存中' : '保存' }}</button></footer>
    </form></section></div></Teleport>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { listResources } from '../../services/resource.service'
import { saveWebFeature } from '../../services/web-feature.service'
import type { ResourceItem } from '../../types/resource'
import type { WebFeaturePayload } from '../../types/web-feature'
import GenerationCandidateEditor from '../generation/GenerationCandidateEditor.vue'
import WebParameterEditor from './WebParameterEditor.vue'
const props = defineProps<{ visible: boolean; groupId: number; projectId: number; feature?: ResourceItem | null }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const empty = (): WebFeaturePayload => ({ name: '', feature_type: 'query', description: '', status: 'active', auth_id: null, parameters: [], candidate: null })
const form = ref<WebFeaturePayload>(empty()), auths = ref<ResourceItem[]>([]), tab = ref('basic'), saving = ref(false), scriptValid = ref(true), error = ref('')
const parametersValid = ref(true)
const tabs = [{ key: 'basic', label: '基本信息' }, { key: 'parameters', label: '输入参数' }, { key: 'script', label: '操作与断言' }]
const types = { page: '页面', login: '登录', query: '查询', add: '新增', edit: '编辑', delete: '删除', detail: '详情', import: '导入', export: '导出', audit: '审核', submit: '提交', other: '其他' }
let epoch = 0
watch(() => [props.visible, props.feature?.id], async () => {
  const version = ++epoch
  if (!props.visible) return
  tab.value = 'basic'; error.value = ''; scriptValid.value = true; parametersValid.value = true
  const data = (props.feature?.data || {}) as Record<string, any>
  form.value = { ...empty(), name: props.feature?.name || '', description: props.feature?.description || '', status: props.feature?.status || 'active', feature_type: data.feature_type || 'query', auth_id: data.auth_id || null, parameters: JSON.parse(JSON.stringify(data.parameters || [])), candidate: JSON.parse(JSON.stringify(data.candidate || null)), expected_revision: Number(data.revision || 0) }
  try { const result = await listResources('/project-auth', { project_id: props.projectId, pageSize: 200 }); if (version === epoch) auths.value = result.items.filter(a => a.project_id === props.projectId) }
  catch (e) { if (version === epoch) error.value = e instanceof Error ? e.message : '加载鉴权失败' }
})
function close() { if (!saving.value) emit('close') }
async function save() {
  if (!form.value.name || !scriptValid.value || !parametersValid.value) return
  saving.value = true; error.value = ''
  try { await saveWebFeature(props.groupId, form.value, props.feature?.id); emit('saved'); emit('close') }
  catch (e) { error.value = e instanceof Error ? e.message : '保存失败' } finally { saving.value = false }
}
</script>
<style scoped>
.modal-backdrop { z-index:1250; } .feature-editor { width:min(940px,calc(100vw - 24px)); max-height:92dvh; display:flex; flex-direction:column; } .feature-editor form { display:flex; flex-direction:column; min-height:0; } main { overflow:auto; padding:18px; min-height:0; } .modal-header button { display:flex; width:32px; height:32px; align-items:center; justify-content:center; padding:0; } .editor-tabs { display:flex; gap:8px; padding:0 18px; border-bottom:1px solid #e2e8f0; } .editor-tabs button { border:0; border-bottom:2px solid transparent; border-radius:0; padding:12px 8px; } .editor-tabs .active { border-bottom-color:#087a87; color:#087a87; } .error { color:#b42318; } .empty { color:#667085; padding:24px 0; text-align:center; }
</style>
