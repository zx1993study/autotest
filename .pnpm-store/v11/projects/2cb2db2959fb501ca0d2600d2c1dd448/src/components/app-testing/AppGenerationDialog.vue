<template>
  <div v-if="visible && mode === 'device'" class="live-backdrop" @click.self="$emit('close')"><section class="live-dialog" role="dialog" aria-modal="true" aria-labelledby="app-live-title"><header><h3 id="app-live-title">APP 设备对话</h3><button type="button" :disabled="active" @click="mode='script'">仅生成脚本</button><button type="button" title="关闭" aria-label="关闭" @click="$emit('close')"><X :size="18" /></button></header><AppLiveGeneration :feature="feature" @active="active=$event" @saved="$emit('saved')" /></section></div>
  <BusinessGenerationDrawer v-if="visible && mode === 'script'" :visible="true" domain="APP" :source-id="feature.id" :source-name="feature.name" @close="mode='device';$emit('close')" @saved="$emit('saved')" />
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { X } from 'lucide-vue-next'
import type { AppFeature } from '../../types/app-feature'
import BusinessGenerationDrawer from '../generation/BusinessGenerationDrawer.vue'
import AppLiveGeneration from './AppLiveGeneration.vue'
defineProps<{visible:boolean;feature:AppFeature}>()
defineEmits<{close:[];saved:[]}>()
const mode=ref('device'),active=ref(false)
</script>
<style scoped>
.live-backdrop { position:fixed; inset:0; z-index:1200; background:#0006; display:flex; justify-content:center; align-items:center; padding:16px; } .live-dialog { width:min(1120px,100%); height:calc(100dvh - 32px); display:flex; flex-direction:column; background:#fff; border-radius:6px; overflow:hidden; box-shadow:0 8px 28px #0002; } header { padding:16px 20px; display:flex; align-items:center; gap:12px; border-bottom:1px solid #e3e8ed; } h3 { flex:1; margin:0; font-size:18px; } header button[aria-label] { width:32px; height:32px; padding:6px; flex-shrink:0; } @media(max-width:760px) { .live-backdrop { padding:0; } .live-dialog { height:100dvh; border-radius:0; } header { padding:12px; } }
</style>
