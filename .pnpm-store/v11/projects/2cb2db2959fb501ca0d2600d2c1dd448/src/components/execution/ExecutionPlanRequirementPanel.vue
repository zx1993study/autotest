<template>
  <details v-if="requirementDocument" class="requirement-panel">
    <summary>
      <strong>需求来源</strong>
      <span>{{ requirementTitle || '页面需求文档' }}</span>
    </summary>
    <pre>{{ requirementDocument }}</pre>
  </details>
</template>

<script setup lang="ts">
defineProps<{
  requirementTitle?: string | null
  requirementDocument?: string | null
}>()
</script>

<style scoped>
.requirement-panel {
  margin: 0 0 18px;
  border: 1px solid #dce4ef;
  border-radius: 6px;
  background: #ffffff;
}

.requirement-panel summary {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 12px 14px;
  color: #334155;
}

.requirement-panel summary span {
  color: #64748b;
  font-weight: 400;
}

.requirement-panel pre {
  max-height: 320px;
  overflow: auto;
  margin: 0;
  border-top: 1px solid #edf1f7;
  padding: 14px;
  color: #334155;
  font-family: inherit;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
