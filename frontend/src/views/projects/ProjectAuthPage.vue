<template>
  <ResourcePage
    title="项目鉴权"
    description="管理 Token、Cookie、API Key、登录用例刷新等项目鉴权配置。"
    api-path="/project-auth"
    :fields="projectAuthFields"
    :columns="projectAuthColumns"
    :row-actions="rowActions"
    :initial-params="projectSearchParams"
    :default-values="projectSearchParams"
    :defer-load="!projectFilterReady"
    :form-blocked="loginCasePickerBlocked"
  >
    <template #search-before-button>
      <ProjectFilterSelect v-model="selectedProjectId" @ready="projectFilterReady = true" />
    </template>
    <template #[loginCaseSlot]="{ values }">
      <ProjectAuthLoginCasePicker
        v-model="values['data.login_case_id']"
        :project-id="values.project_id"
        :case-type="String(values['data.login_case_type'] || 'API')"
        :required="['on_login_success', 'scheduled'].includes(String(values['data.refresh_strategy']))"
        @blocked="loginCasePickerBlocked = $event"
      />
    </template>
    <template #form-field-data.token="{ values, item }">
      <ProjectAuthTokenInput :model-value="values['data.token']" :has-file="Boolean(item?.data.token_file)" @update:model-value="values['data.token'] = $event" />
    </template>
  </ResourcePage>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import ProjectFilterSelect from '../../components/filters/ProjectFilterSelect.vue'
import ResourcePage from '../../components/ResourcePage.vue'
import ProjectAuthLoginCasePicker from '../../components/projects/ProjectAuthLoginCasePicker.vue'
import ProjectAuthTokenInput from '../../components/projects/ProjectAuthTokenInput.vue'
import { projectAuthColumns, projectAuthFields } from '../../resourceSchemas'
import type { PageAction } from '../../types/page-actions'

const selectedProjectId = ref(0)
const projectFilterReady = ref(false)
const loginCasePickerBlocked = ref(false)
const loginCaseSlot = 'form-field-data.login_case_id'
const projectSearchParams = computed<Record<string, unknown>>(() => (
  selectedProjectId.value ? { project_id: selectedProjectId.value } : {}
))

const rowActions: PageAction[] = [
  {
    label: '刷新',
    path: '/project-auth/{id}/refresh',
    payload: {
      mode: 'local_headless'
    },
    disabledWhen: {
      key: 'status',
      value: ['disabled', 'archived']
    }
  }
]
</script>
