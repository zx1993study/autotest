<template>
  <section class="ai-model-page">
    <article class="current-model">
      <div>
        <span>当前模型</span>
        <h3>{{ currentModel ? currentModel.name : '未配置当前模型' }}</h3>
        <p v-if="currentModel">
          {{ modelProvider(currentModel) }} / {{ modelName(currentModel) }} / {{ modelBaseUrl(currentModel) }}
        </p>
        <p v-else>启用一个模型并设为当前模型后，AI 生成会默认使用它。</p>
      </div>
      <button type="button" @click="loadCurrentModel">刷新</button>
    </article>

    <ResourcePage
      ref="resourcePageRef"
      title="AI 模型配置"
      description="配置 OpenAI 兼容模型，API Key 只保存到服务端文件，数据库只保留文件名。"
      api-path="/ai/models"
      :fields="aiModelFields"
      :columns="aiModelColumns"
      :row-actions="rowActions"
      @custom-action="handleCustomAction"
    />
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listRemoteOptions, postAction, ResourceItem } from '../../api/http'
import ResourcePage from '../../components/ResourcePage.vue'
import { aiModelColumns, aiModelFields } from '../../resourceSchemas'
import type { PageAction } from '../../types/page-actions'

const resourcePageRef = ref<{ load: () => Promise<void> } | null>(null)
const currentModel = ref<ResourceItem | null>(null)

const rowActions: PageAction[] = [
  {
    label: '设为当前',
    path: '',
    type: 'custom',
    name: 'set-current',
    enabledWhen: {
      key: 'status',
      value: 'active'
    }
  }
]

async function loadCurrentModel() {
  currentModel.value = (await listRemoteOptions('/ai/models/current')) as unknown as ResourceItem | null
}

async function handleCustomAction(action: PageAction, item?: ResourceItem) {
  if (action.name !== 'set-current' || !item) {
    return
  }
  await postAction(`/ai/models/${item.id}/set-current`, {})
  await Promise.all([
    loadCurrentModel(),
    resourcePageRef.value?.load()
  ])
}

function modelProvider(item: ResourceItem) {
  return String(item.data.provider || 'OpenAI兼容')
}

function modelName(item: ResourceItem) {
  return String(item.data.model || '-')
}

function modelBaseUrl(item: ResourceItem) {
  return String(item.data.base_url || '-')
}

onMounted(loadCurrentModel)
</script>

<style scoped>
.ai-model-page {
  display: grid;
  gap: 16px;
}

.current-model {
  align-items: center;
  background: #fff;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  padding: 18px 22px;
}

.current-model span {
  color: #64748b;
  font-size: 13px;
}

.current-model h3 {
  font-size: 18px;
  margin: 4px 0;
}

.current-model p {
  color: #52627a;
  font-size: 13px;
  margin: 0;
}
</style>
