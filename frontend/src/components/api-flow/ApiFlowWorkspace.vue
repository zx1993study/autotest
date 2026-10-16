<template>
  <section class="api-flow">
    <header class="flow-page-header"><div><RouterLink class="flow-back-link" to="/api/flows"><ArrowLeft :size="16" />API 功能管理</RouterLink><h2>{{ flow?.name || '流程详情' }}</h2><p class="flow-muted">{{ flow?.description }}{{ flow?.description ? ' · ' : '' }}模板 v{{ flow?.data.version || 1 }}{{ dirty ? ' · 未保存修改' : '' }}</p></div><button title="刷新" aria-label="刷新流程" :disabled="busy || dirty" @click="load"><RefreshCw :size="17" /></button></header>
    <p v-if="error && !editingScene && !showRunDialog" class="flow-feedback flow-error" role="alert">{{ error }}</p><p v-if="message" class="flow-feedback flow-success" role="status">{{ message }}</p>
    <nav class="flow-tabs"><button v-for="item in tabs" :key="item.key" :class="{active: tab === item.key}" @click="tab = item.key"><component :is="item.icon" :size="16" />{{ item.label }}<span v-if="item.key === 'scenes'">{{ scenes.length }}</span></button></nav>
    <div v-if="loading" class="flow-empty">加载中...</div>
    <template v-else-if="flow">
      <ApiFlowScenarioTable v-if="tab === 'scenes'" v-model:selected="selected" :scenes="scenes" :version="flow.data.version" :busy="busy" @create="createScene" @edit="editScene" @copy="copyScene" @toggle="toggleScene" @sync="syncScene" @delete="deleteScene" @run="openRun" />
      <ApiFlowTemplateEditor v-show="tab === 'template'" v-model="definition" :project-id="Number(flow.project_id)" :apis="apis" :auths="auths" :busy="busy" @save="saveTemplate" />
      <ApiFlowRunPanel v-if="tab === 'runs'" :runs="runs" :current="currentRun" :busy="busy" @refresh="refreshRuns" @select="selectRun" @cancel="cancelRun" />
      <ApiFlowScenarioEditor v-if="editingScene" :scene="editingScene" :definition="flow.data" :project-id="Number(flow.project_id)" :busy="busy" :error="error" @close="editingScene = null" @save="saveScene" />
      <ApiFlowRunDialog v-if="showRunDialog" :scenes="runScenes" :busy="busy" :error="error" @close="showRunDialog = false" @run="startRun" />
    </template>
  </section>
</template>
<script setup lang="ts">
import { onMounted } from 'vue'
import { ArrowLeft, GitBranch, History, ListChecks, RefreshCw } from 'lucide-vue-next'
import { useApiFlowWorkspace } from '../../composables/useApiFlowWorkspace'
import ApiFlowScenarioTable from './ApiFlowScenarioTable.vue'
import ApiFlowTemplateEditor from './ApiFlowTemplateEditor.vue'
import ApiFlowScenarioEditor from './ApiFlowScenarioEditor.vue'
import ApiFlowRunDialog from './ApiFlowRunDialog.vue'
import ApiFlowRunPanel from './ApiFlowRunPanel.vue'
const props = defineProps<{flowId: number}>()
const {flow, definition, scenes, runs, currentRun, apis, auths, selected, tab, busy, loading, error, message,
  editingScene, runScenes, showRunDialog, dirty, load, saveTemplate, createScene, editScene, saveScene,
  copyScene, toggleScene, deleteScene, syncScene, openRun, startRun, selectRun, cancelRun, refreshRuns} = useApiFlowWorkspace(props.flowId)
const tabs = [{key: 'scenes', label: '功能场景', icon: ListChecks}, {key: 'template', label: '流程模板', icon: GitBranch}, {key: 'runs', label: '运行记录', icon: History}]
onMounted(load)
</script>
<style src="../../styles/api-flow.css"></style>
