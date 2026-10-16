<template>
  <section v-if="stages?.length" class="progress"><h4>AI 处理进度</h4><ol><li v-for="(stage,index) in stages" :key="`${stage.code}:${index}`"><CheckCircle2 v-if="stage.status === 'success'" :size="16" class="success" /><XCircle v-else-if="stage.status === 'failed' || status === 'canceled'" :size="16" class="failed" /><LoaderCircle v-else :size="16" /><span>{{ stage.label }}</span><small v-if="stage.status === 'running' && status === 'canceled'">已中止</small></li></ol></section>
  <section v-if="steps.length" class="plan"><h4>待执行操作 <small>{{ steps.length }} 步</small></h4><ol><li v-for="(step,index) in steps" :key="index"><span class="order">{{ index+1 }}</span><div><strong>{{ step.name || step.action }}</strong><small>{{ actions[step.action] || step.action }}<template v-if="step.locator"> · {{ step.locator }}</template></small></div></li></ol></section>
  <section v-for="(record,index) in records || []" :key="index" class="executed"><h4>{{ record.name || '实际执行' }}</h4><ol><li v-for="(step,order) in record.data?.steps || []" :key="order"><CheckCircle2 v-if="order < (record.data?.step_count || 0)" :size="16" class="success" /><XCircle v-else-if="record.status === 'failed' && order === (record.data?.step_count || 0)" :size="16" class="failed" /><Circle v-else :size="16" /><span>{{ step.name || step.action }}</span><small>{{ order < (record.data?.step_count || 0) ? '已执行' : record.status === 'failed' && order === (record.data?.step_count || 0) ? '失败' : '未执行' }}</small></li></ol></section>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { CheckCircle2, XCircle, LoaderCircle, Circle } from 'lucide-vue-next'
import type { GenerationStage } from '../../types/generation'
const props = defineProps<{ stages?:GenerationStage[]; status?:string; candidate:Record<string,any> | null; records?:any[] }>()
const steps = computed(() => props.candidate?.steps || [])
const actions:Record<string,string> = { tap:'点击', click:'点击', input:'输入', fill:'输入', manual:'人工输入', assert:'断言', assert_text:'断言', swipe:'滑动', select:'选择', wait:'等待', check:'勾选', uncheck:'取消勾选' }
</script>
<style scoped>
section { border-bottom:1px solid #e3e8ed; padding:0 0 14px; margin-bottom:16px; } h4 { font-size:14px; margin:0 0 12px; } ol { list-style:none; padding:0; margin:0; } li { display:flex; gap:10px; align-items:flex-start; padding:7px 0; min-width:0; font-size:13px; }
li>span,li>div { overflow-wrap:anywhere; min-width:0; } li svg { flex-shrink:0; margin-top:2px; } small { color:#667085; font-size:12px; } li div small { display:block; margin-top:3px; } strong { font-weight:500; }
.order { flex:0 0 22px; height:22px; border:1px solid #e3e8ed; border-radius:4px; text-align:center; line-height:20px; color:#667085; } .success { color:#18835b; } .failed { color:#b42318; }
</style>
