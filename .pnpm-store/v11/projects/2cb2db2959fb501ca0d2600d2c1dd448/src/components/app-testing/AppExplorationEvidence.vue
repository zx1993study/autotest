<template>
  <section class="evidence">
    <div class="state"><strong>{{ label }}</strong><span>已完成 {{ task?.live.cursor || 0 }} 步</span><small>模型调用 {{ task?.live.model_http_calls || 0 }} 次</small></div>
    <div class="screen"><img v-if="task?.live.preview?.screenshot_url" :src="media(task.live.preview.screenshot_url)" alt="设备当前界面" /><MonitorSmartphone v-else :size="46" /><span v-if="task?.live.observed_at" class="capture-time">{{ new Date(task.live.observed_at).toLocaleTimeString() }}</span></div>
    <p v-if="task?.live.session_reused != null" class="session-state">{{ task.live.session_reused ? '已复用设备 session' : '已建立设备 session' }}</p>
    <dl v-if="task?.live.connection || task?.bundle_id || task?.live.app_candidate" class="connection-info">
      <template v-if="task?.live.connection"><dt>WDA 已连接</dt><dd>{{ task.live.connection.wda_url }}</dd></template>
      <template v-if="task?.bundle_id"><dt>应用已绑定</dt><dd>{{ task.bundle_id }}</dd></template>
      <template v-else-if="task?.live.app_candidate"><dt>待确认应用</dt><dd>{{ task.live.app_candidate.app_name || '名称未识别' }}<br />{{ task.live.app_candidate.bundle_id }}</dd></template>
    </dl>
    <p v-if="task?.error" role="alert" class="error">{{ task.error }}</p>
    <p v-else-if="task?.result?.records?.[0]?.data?.error" role="alert" class="error">{{ task.result.records[0].data.error }}</p>
    <p v-if="task?.live.outcome_unknown" role="alert" class="error">上一操作结果未知，不会自动重试。请先检查手机。</p>
    <nav><button type="button" :class="{active:tab === 'steps'}" @click="tab='steps'">执行步骤</button><button type="button" :class="{active:tab === 'inputs'}" @click="tab='inputs'">输入信息</button></nav>
    <ol v-if="tab === 'steps'"><li v-for="(step,index) in task?.live.timeline || []" :key="step.nonce"><CheckCircle2 v-if="step.status === 'success'" :size="16" class="success" /><CircleAlert v-else :size="16" class="error" /><div><strong>{{ index+1 }}. {{ step.name }}</strong><small>{{ statuses[step.status] || step.status }} · {{ step.duration_ms }} ms</small><small v-if="step.error">{{ step.error }}</small></div></li><li v-if="task?.live.command"><LoaderCircle :size="16" /><span>{{ task.live.command.step.name }}</span></li></ol>
    <dl v-else><template v-for="(value,key) in task?.live.input_info || {}" :key="key"><dt>{{ key }}</dt><dd>{{ value?.value ?? value }}</dd></template></dl>
    <details v-if="task?.live.events.length"><summary>AI 活动记录</summary><p v-for="(event,index) in task.live.events" :key="index">{{ event.label }}</p></details>
    <video v-if="video" :src="media(video)" controls preload="metadata" />
  </section>
</template>
<script setup lang="ts">
import { computed,ref } from 'vue'
import { MonitorSmartphone,CheckCircle2,CircleAlert,LoaderCircle } from 'lucide-vue-next'
import type { AppExploration } from '../../types/app-exploration'
import { withScreenshotAccessToken as media } from '../../utils/screenshotUrl'
const props = defineProps<{task:AppExploration|null;label:string}>()
const tab = ref('steps')
const statuses:Record<string,string> = {success:'成功',failed:'失败',stale:'界面变化，未操作'}
const video = computed(() => props.task?.result?.records?.[0]?.data?.video_url)
</script>
<style scoped>
.evidence { min-width:0; } .state { display:flex; gap:12px; align-items:center; flex-wrap:wrap; font-size:13px; margin-bottom:12px; } .state small { color:#667085; }
.screen { min-height:240px; max-height:360px; position:relative; background:#f3f5f7; display:flex; justify-content:center; align-items:center; overflow:hidden; } .screen img { display:block; max-height:360px; max-width:100%; object-fit:contain; } .capture-time { position:absolute; right:8px; bottom:6px; font-size:11px; background:#fff; padding:3px 6px; }
.session-state { color:#667085; font-size:12px; } nav { display:flex; border-bottom:1px solid #e3e8ed; margin-top:16px; } nav button { border:0; border-radius:0; padding:10px 14px; } .active { border-bottom:2px solid #087f8c; color:#087f8c; }
ol { list-style:none; padding:0; } li { display:flex; gap:9px; padding:9px 0; font-size:13px; } li svg { flex-shrink:0; margin-top:2px; } li div { min-width:0; overflow-wrap:anywhere; } li strong { font-weight:500; } li small { display:block; color:#667085; margin-top:5px; }
.success { color:#18835b; } .error { color:#b42318; font-size:13px; } dl { display:grid; grid-template-columns:minmax(80px,1fr) minmax(0,2fr); font-size:13px; gap:12px; } dt,dd { margin:0; overflow-wrap:anywhere; } details { font-size:12px; border-top:1px solid #e3e8ed; padding:12px 0; } video { width:100%; max-height:320px; }
</style>
