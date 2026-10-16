<template>
  <div class="parameter-region"><h3>输入参数 <small>{{ parameters.length }}</small></h3>
    <div class="table-wrap"><table><thead><tr><th>字段名称</th><th>类型</th><th>必填</th><th>选项 / 规则</th><th>状态</th></tr></thead>
      <tbody><tr v-for="p in parameters" :key="p.key" :class="{ selected: selected === p.key }" @click="$emit('select',p.key)">
        <td><strong>{{ p.label }}</strong><small>{{ p.key }}</small></td><td>{{ types[p.type] }}</td><td>{{ p.required_known === false ? '待确认' : p.required ? '是' : '否' }}</td>
        <td>{{ p.options?.length ? p.options.map(optionText).join('、') : Object.keys(p.validation || {}).length ? JSON.stringify(p.validation) : '-' }}<small v-if="p.condition?.key">{{ p.condition.key }} = {{ p.condition.equals }}</small></td>
        <td>{{ p.confirmed ? '已确认' : '待确认' }}</td>
      </tr><tr v-if="!parameters.length"><td colspan="5" class="empty">暂无输入参数</td></tr></tbody>
    </table></div>
  </div>
</template>
<script setup lang="ts">
import type { WebParameter } from '../../types/web-feature'
defineProps<{ parameters: WebParameter[]; selected?: string }>()
defineEmits<{ select: [key: string] }>()
const types: Record<string,string> = { text:'文本', password:'密码', textarea:'多行文本', number:'数字', select:'下拉框', multiselect:'多选框', date:'日期', datetime:'日期时间', boolean:'开关', json:'结构化数据', manual:'人工输入' }
function optionText(option: any) { return typeof option === 'object' && option ? option.label ?? option.value : option }
</script>
<style scoped>
.parameter-region { min-width:0; } h3 { font-size:15px; margin:0 0 12px; } small { color:#667085; font-size:12px; } td small { display:block; margin-top:5px; } table { table-layout:fixed; min-width:480px; } th:first-child { width:26%; } th:nth-child(2) { width:85px; } th:nth-child(3) { width:64px; } th:last-child { width:70px; } td { overflow-wrap:anywhere; } tr.selected { background:#eaf8f7; } .empty { text-align:center; padding:32px 12px; color:#667085; }
</style>
