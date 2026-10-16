<template>
  <section class="page system-user-page">
    <header class="page-header">
      <div>
        <h2>用户管理</h2>
        <p>维护平台登录账号、实名、手机号与密码状态，用户名全局唯一。</p>
      </div>
      <button type="button" @click="openCreateDialog">新增用户</button>
    </header>

    <div class="toolbar">
      <input v-model.trim="filters.keyword" placeholder="搜索用户名、实名或手机号" @keyup.enter="reload(1)" />
      <select v-model="filters.status" aria-label="状态">
        <option value="">全部状态</option>
        <option value="active">启用</option>
        <option value="disabled">停用</option>
      </select>
      <button type="button" @click="reload(1)">查询</button>
      <button type="button" class="secondary-button" @click="resetFilters">重置</button>
    </div>

    <div class="table-wrap">
      <table :aria-busy="loading">
        <thead>
          <tr>
            <th>用户名</th>
            <th>实名</th>
            <th>手机号码</th>
            <th>登录密码信息</th>
            <th>状态</th>
            <th>最近登录</th>
            <th>更新时间</th>
            <th class="action-column">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td class="empty-cell" colspan="8">加载中...</td>
          </tr>
          <tr v-else-if="message && rows.length === 0">
            <td class="empty-cell" colspan="8">{{ message }}</td>
          </tr>
          <tr v-else-if="rows.length === 0">
            <td class="empty-cell" colspan="8">暂无用户</td>
          </tr>
          <tr v-for="row in rows" v-else :key="row.id">
            <td class="table-cell">{{ row.username }}</td>
            <td class="table-cell">{{ row.real_name || '-' }}</td>
            <td>{{ row.phone || '-' }}</td>
            <td>{{ row.password_info }}</td>
            <td>
              <span class="status-pill" :class="statusCodeOf(row.status)">
                {{ statusLabel(row.status) }}
              </span>
            </td>
            <td>{{ formatLoginTime(row.last_login_at) }}</td>
            <td>{{ row.updated_at || '-' }}</td>
            <td>
              <div class="row-actions">
                <button type="button" class="link-button" @click="openEditDialog(row)">编辑</button>
                <button type="button" class="link-button" @click="openResetPasswordDialog(row)">重置密码</button>
                <button type="button" class="link-button danger" @click="removeUser(row)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer class="pager">
      <div class="pager-info">
        共 {{ total }} 条
        <span v-if="message" class="pager-message">{{ message }}</span>
      </div>
      <div class="pager-controls">
        <button type="button" :disabled="loading || pagination.page <= 1" @click="reload(pagination.page - 1)">上一页</button>
        <span>第 {{ pagination.page }} 页</span>
        <button type="button" :disabled="loading || pagination.page * pagination.pageSize >= total" @click="reload(pagination.page + 1)">
          下一页
        </button>
      </div>
    </footer>

    <div v-if="toast.visible" class="operation-toast" role="status" aria-live="polite">
      <strong>操作成功</strong>
      <span>{{ toast.message }}</span>
    </div>

    <div v-if="userDialog.visible" class="modal-backdrop">
      <section class="modal-panel">
        <header class="modal-header">
          <h3>{{ userDialog.mode === 'create' ? '新增用户' : '编辑用户' }}</h3>
          <button type="button" class="modal-close" aria-label="关闭" @click="closeUserDialog">×</button>
        </header>
        <form class="modal-form" @submit.prevent="submitUserForm">
          <div class="form-grid">
            <label class="field">
              用户名 <b>*</b>
              <input v-model.trim="userForm.username" autocomplete="off" maxlength="64" />
            </label>
            <label class="field">
              实名 <b>*</b>
              <input v-model.trim="userForm.real_name" autocomplete="off" maxlength="64" />
            </label>
            <label class="field">
              手机号码
              <input v-model.trim="userForm.phone" autocomplete="off" maxlength="32" />
            </label>
            <label class="field">
              状态 <b>*</b>
              <select v-model="userForm.status">
                <option value="active">启用</option>
                <option value="disabled">停用</option>
              </select>
            </label>
            <label v-if="userDialog.mode === 'create'" class="field full">
              登录密码 <b>*</b>
              <input v-model="userForm.password" type="password" autocomplete="new-password" maxlength="128" />
            </label>
          </div>
          <p v-if="formError" class="form-error">{{ formError }}</p>
          <div class="modal-actions">
            <button type="button" class="secondary-button" @click="closeUserDialog">取消</button>
            <button type="submit" :disabled="submitting">{{ submitting ? '保存中...' : '保存' }}</button>
          </div>
        </form>
      </section>
    </div>

    <div v-if="resetDialog.visible" class="modal-backdrop">
      <section class="modal-panel reset-password-panel">
        <header class="modal-header">
          <h3>重置密码</h3>
          <button type="button" class="modal-close" aria-label="关闭" @click="closeResetPasswordDialog">×</button>
        </header>
        <form class="modal-form" @submit.prevent="submitResetPassword">
          <label class="field">
            用户
            <input :value="resetDialog.user?.username || ''" disabled />
          </label>
          <label class="field">
            新密码 <b>*</b>
            <input v-model="resetPasswordForm.password" type="password" autocomplete="new-password" maxlength="128" />
          </label>
          <p v-if="formError" class="form-error">{{ formError }}</p>
          <div class="modal-actions">
            <button type="button" class="secondary-button" @click="closeResetPasswordDialog">取消</button>
            <button type="submit" :disabled="submitting">{{ submitting ? '提交中...' : '确认重置' }}</button>
          </div>
        </form>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { useLatestRequest } from '../../composables/useLatestRequest'
import {
  createSystemUser,
  deleteSystemUser,
  listSystemUsers,
  resetSystemUserPassword,
  updateSystemUser
} from '../../services/system-user.service'
import type { SystemUser } from '../../types/system-user'

const rows = ref<SystemUser[]>([])
const total = ref(0)
const { loading, error: message, run: loadUsers } = useLatestRequest('用户加载失败')
const submitting = ref(false)
const formError = ref('')
let toastTimer: number | undefined

const filters = reactive({
  keyword: '',
  status: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20
})

const userDialog = reactive<{
  visible: boolean
  mode: 'create' | 'edit'
  user: SystemUser | null
}>({
  visible: false,
  mode: 'create',
  user: null
})

const userForm = reactive({
  username: '',
  real_name: '',
  phone: '',
  password: '',
  status: 'active'
})

const resetDialog = reactive<{
  visible: boolean
  user: SystemUser | null
}>({
  visible: false,
  user: null
})

const resetPasswordForm = reactive({
  password: ''
})

const toast = reactive({
  visible: false,
  message: ''
})

onMounted(() => {
  void reload(1)
})

async function reload(page = pagination.page) {
  await loadUsers(signal => listSystemUsers({
      keyword: filters.keyword || undefined,
      status: filters.status || undefined,
      page,
      pageSize: pagination.pageSize
    }, signal), result => {
    rows.value = result.items
    total.value = result.total
    pagination.page = result.page
    pagination.pageSize = result.pageSize
  })
}

function resetFilters() {
  filters.keyword = ''
  filters.status = ''
  void reload(1)
}

function openCreateDialog() {
  userDialog.visible = true
  userDialog.mode = 'create'
  userDialog.user = null
  formError.value = ''
  Object.assign(userForm, {
    username: '',
    real_name: '',
    phone: '',
    password: '',
    status: 'active'
  })
}

function openEditDialog(user: SystemUser) {
  userDialog.visible = true
  userDialog.mode = 'edit'
  userDialog.user = user
  formError.value = ''
  Object.assign(userForm, {
    username: user.username,
    real_name: user.real_name,
    phone: user.phone || '',
    password: '',
    status: statusCodeOf(user.status)
  })
}

function closeUserDialog() {
  userDialog.visible = false
  userDialog.user = null
  formError.value = ''
}

async function submitUserForm() {
  formError.value = validateUserForm()
  if (formError.value) {
    return
  }
  submitting.value = true
  try {
    if (userDialog.mode === 'create') {
      await createSystemUser({
        username: userForm.username,
        real_name: userForm.real_name,
        phone: userForm.phone || null,
        password: userForm.password,
        status: userForm.status
      })
      showToast('用户已新增')
    } else if (userDialog.user) {
      await updateSystemUser(userDialog.user.id, {
        username: userForm.username,
        real_name: userForm.real_name,
        phone: userForm.phone || null,
        status: userForm.status
      })
      showToast('用户信息已更新')
    }
    closeUserDialog()
    await reload(pagination.page)
  } catch (error) {
    formError.value = getErrorMessage(error)
  } finally {
    submitting.value = false
  }
}

function openResetPasswordDialog(user: SystemUser) {
  resetDialog.visible = true
  resetDialog.user = user
  resetPasswordForm.password = ''
  formError.value = ''
}

function closeResetPasswordDialog() {
  resetDialog.visible = false
  resetDialog.user = null
  formError.value = ''
}

async function submitResetPassword() {
  const password = resetPasswordForm.password.trim()
  if (password.length < 6) {
    formError.value = '新密码至少 6 位'
    return
  }
  if (!resetDialog.user) {
    return
  }
  submitting.value = true
  try {
    await resetSystemUserPassword(resetDialog.user.id, password)
    closeResetPasswordDialog()
    showToast('密码已重置')
    await reload(pagination.page)
  } catch (error) {
    formError.value = getErrorMessage(error)
  } finally {
    submitting.value = false
  }
}

async function removeUser(user: SystemUser) {
  if (!window.confirm(`确认删除用户「${user.username}」？`)) {
    return
  }
  try {
    await deleteSystemUser(user.id)
    showToast('用户已删除')
    await reload(rows.value.length === 1 && pagination.page > 1 ? pagination.page - 1 : pagination.page)
  } catch (error) {
    message.value = getErrorMessage(error)
  }
}

function validateUserForm() {
  if (!userForm.username.trim()) {
    return '请输入用户名'
  }
  if (!/^[A-Za-z0-9_.@-]+$/.test(userForm.username.trim())) {
    return '用户名仅支持字母、数字、下划线、点、@ 和短横线'
  }
  if (!userForm.real_name.trim()) {
    return '请输入实名'
  }
  if (userDialog.mode === 'create' && userForm.password.trim().length < 6) {
    return '登录密码至少 6 位'
  }
  return ''
}

function statusCodeOf(status: string) {
  if (status === '启用' || status === 'active') {
    return 'active'
  }
  if (status === '停用' || status === 'disabled') {
    return 'disabled'
  }
  return 'queued'
}

function statusLabel(status: string) {
  if (status === 'active') {
    return '启用'
  }
  if (status === 'disabled') {
    return '停用'
  }
  return status || '-'
}

function formatLoginTime(value?: number | null) {
  if (!value) {
    return '-'
  }
  return new Date(value * 1000).toLocaleString()
}

function showToast(text: string) {
  toast.message = text
  toast.visible = true
  if (toastTimer) {
    window.clearTimeout(toastTimer)
  }
  toastTimer = window.setTimeout(() => {
    toast.visible = false
  }, 3000)
}

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : '操作失败'
}
</script>

<style scoped>
.system-user-page .toolbar select {
  width: 128px;
  height: 38px;
  border: 1px solid #d8e0ef;
  border-radius: 6px;
  background: #ffffff;
  padding: 0 10px;
}

.secondary-button {
  border-color: #d8e0ef;
  background: #ffffff;
  color: #39465e;
}

.link-button {
  border: 0;
  background: transparent;
  color: #2368e8;
  padding: 0;
}

.link-button.danger {
  color: #c73535;
}

.status-pill.active {
  border: 1px solid #bde7ce;
  color: #168044;
  background: #effaf3;
}

.status-pill.disabled {
  border: 1px solid #d7deea;
  color: #62708a;
  background: #f8fafd;
}

.reset-password-panel {
  width: min(520px, 100%);
}
</style>
