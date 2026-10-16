<template>
  <div class="flow-backdrop" @click.self="emit('close')"><section class="flow-dialog flow-run-dialog" role="dialog" aria-modal="true" aria-label="执行功能场景">
    <header class="flow-dialog-header"><h3>执行 {{ scenes.length }} 个功能场景</h3><button title="关闭" aria-label="关闭" @click="emit('close')"><X :size="18" /></button></header>
    <div class="flow-dialog-body"><div class="flow-run-scene-names"><span v-for="scene in scenes" :key="scene.id">{{ scene.name }}</span></div>
      <div class="flow-form-grid"><label>执行模式<div class="flow-segments"><button :class="{active: draft.mode === 'serial'}" @click="draft.mode = 'serial'">串行</button><button :class="{active: draft.mode === 'parallel'}" @click="draft.mode = 'parallel'">并行</button></div></label><label v-if="draft.mode === 'parallel'">并发数<input v-model.number="draft.concurrency" type="number" min="1" max="4" /></label></div>
      <FlowParametersEditor v-model="draft.inputs" title="本次输入覆盖" />
      <p v-if="error" class="flow-error">{{ error }}</p>
    </div><footer class="flow-dialog-footer"><button @click="emit('close')">取消</button><button class="primary" :disabled="busy" @click="emit('run', draft)"><Play :size="16" />开始执行</button></footer>
  </section></div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { Play, X } from 'lucide-vue-next'
import type { ApiFlowRunRequest, ApiFlowScenario } from '../../types/api-flow'
import FlowParametersEditor from './FlowParametersEditor.vue'
const props = defineProps<{scenes: ApiFlowScenario[]; busy: boolean; error: string}>()
const emit = defineEmits<{(event: 'close'): void; (event: 'run', payload: ApiFlowRunRequest): void}>()
const draft = ref<ApiFlowRunRequest>({scenario_ids: props.scenes.map(scene => scene.id), mode: 'serial', concurrency: 2, inputs: {}})
</script>
