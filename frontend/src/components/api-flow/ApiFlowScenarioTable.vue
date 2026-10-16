<template>
  <section>
    <div class="flow-toolbar"><div class="flow-actions"><input v-model="keyword" placeholder="搜索场景名称" aria-label="搜索场景名称" /><select v-model="filter" aria-label="场景状态"><option value="all">全部场景</option><option value="active">启用</option><option value="disabled">停用</option><option value="stale">待同步模板</option></select></div>
      <div class="flow-actions"><button :disabled="busy" @click="emit('create')"><Plus :size="16" />新增场景</button><button class="primary" :disabled="busy || !selected.length" @click="emit('run', selected)"><Play :size="16" />执行所选 ({{ selected.length }})</button></div>
    </div>
    <div class="flow-table-wrap"><table><thead><tr><th class="flow-check-cell"><input type="checkbox" :checked="allChecked" aria-label="选择所有可执行场景" @change="toggleAll(($event.target as HTMLInputElement).checked)" /></th><th>功能场景</th><th>状态</th><th>模板版本</th><th>最近结果</th><th>操作</th></tr></thead>
      <tbody><tr v-for="scene in filtered" :key="scene.id">
        <td><input v-model="selected" type="checkbox" :value="scene.id" :disabled="!canRun(scene)" :aria-label="`选择${scene.name}`" /></td>
        <td><strong>{{ scene.name }}</strong><small class="flow-table-note">{{ scene.description || '无备注' }}</small></td>
        <td><label class="flow-checkbox"><input type="checkbox" :checked="scene.status === 'active'" :disabled="busy" @change="emit('toggle', scene)" />{{ flowStatusLabels[scene.status] || scene.status }}</label></td>
        <td><span :class="{'flow-warning': stale(scene)}">v{{ scene.data.template_version }}{{ stale(scene) ? ' · 待同步' : '' }}</span></td>
        <td><span class="flow-status" :class="scene.data.latest_status">{{ flowStatusLabels[scene.data.latest_status || ''] || '未执行' }}</span></td>
        <td class="flow-actions"><button v-if="stale(scene)" :disabled="busy" @click="emit('sync', scene)"><RefreshCw :size="14" />同步</button><button v-else :disabled="busy" @click="emit('edit', scene)">配置</button><button title="复制场景" aria-label="复制场景" :disabled="busy || stale(scene)" @click="emit('copy', scene)"><Copy :size="15" /></button><button title="执行场景" aria-label="执行场景" :disabled="busy || !canRun(scene)" @click="emit('run', [scene.id])"><Play :size="15" /></button><button class="flow-danger" title="删除场景" aria-label="删除场景" :disabled="busy" @click="emit('delete', scene)"><Trash2 :size="15" /></button></td>
      </tr><tr v-if="!filtered.length"><td colspan="6" class="flow-empty">暂无功能场景</td></tr></tbody>
    </table></div>
  </section>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Copy, Play, Plus, RefreshCw, Trash2 } from 'lucide-vue-next'
import { flowStatusLabels } from '../../types/api-flow'
import type { ApiFlowScenario } from '../../types/api-flow'
const props = defineProps<{scenes: ApiFlowScenario[]; version: number; busy: boolean}>()
const emit = defineEmits<{(event: 'create'): void; (event: 'run', ids: number[]): void; (event: 'edit' | 'copy' | 'sync' | 'delete' | 'toggle', scene: ApiFlowScenario): void}>()
const selected = defineModel<number[]>('selected', {required: true})
const keyword = ref('')
const filter = ref('all')
const stale = (scene: ApiFlowScenario) => scene.data.template_version !== props.version
const canRun = (scene: ApiFlowScenario) => scene.status === 'active' && !stale(scene)
const filtered = computed(() => props.scenes.filter(scene => scene.name.includes(keyword.value) && (filter.value === 'all' || (filter.value === 'stale' ? stale(scene) : scene.status === filter.value))))
const selectable = computed(() => filtered.value.filter(canRun).map(scene => scene.id))
const allChecked = computed(() => selectable.value.length > 0 && selectable.value.every(id => selected.value.includes(id)))
function toggleAll(checked: boolean) { selected.value = checked ? [...new Set([...selected.value, ...selectable.value])] : selected.value.filter(id => !selectable.value.includes(id)) }
watch(() => [props.scenes, props.version], () => { selected.value = selected.value.filter(id => props.scenes.some(scene => scene.id === id && canRun(scene))) }, {deep: true})
</script>
