<template>
  <main class="login-page">
    <section class="login-panel" aria-label="登录">
      <form class="login-form" @submit.prevent="submit">
        <label class="login-field">
          <span>账号</span>
          <input
            v-model.trim="form.username"
            autocomplete="username"
            autofocus
            placeholder="请输入账号"
            :disabled="submitting"
          />
        </label>

        <label class="login-field login-password-field">
          <span>密码</span>
          <div class="login-password-control">
            <input
              v-model="form.password"
              autocomplete="current-password"
              placeholder="请输入密码"
              type="password"
              :disabled="submitting"
            />
            <small>{{ passwordPolicy }}</small>
          </div>
        </label>

        <label class="remember-password">
          <input v-model="rememberPassword" type="checkbox" :disabled="submitting" />
          <span>记住密码</span>
        </label>

        <p v-if="errorMessage" class="login-error">{{ errorMessage }}</p>

        <button type="submit" :disabled="submitting">
          {{ submitting ? '登录中...' : '登录' }}
        </button>
      </form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiClientError } from '../../api/client'
import { DEFAULT_AUTHENTICATED_PATH } from '../../constants/routes'
import { getAuthBootstrap } from '../../services/auth.service'
import { useAuthStore } from '../../store/auth'
import { appPath } from '../../utils/appBase'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const submitting = ref(false)
const errorMessage = ref('')
const passwordPolicy = ref('至少 6 位，建议包含大小写字母、数字和符号。')
const rememberPassword = ref(false)
const form = reactive({
  username: '',
  password: ''
})
const rememberedPasswordKey = 'autotest.login.rememberedPassword'

onMounted(async () => {
  const remembered = readRememberedPassword()
  if (remembered) {
    form.username = remembered.username
    form.password = remembered.password
    rememberPassword.value = true
  }
  try {
    const info = await getAuthBootstrap()
    if (!remembered) {
      form.username = info.default_username || ''
    }
    passwordPolicy.value = info.password_policy || passwordPolicy.value
  } catch {
    if (!remembered) {
      form.username = 'admin'
    }
  }
})

async function submit() {
  if (!form.username || !form.password) {
    errorMessage.value = '请输入账号和密码'
    return
  }
  submitting.value = true
  errorMessage.value = ''
  try {
    await authStore.login({ username: form.username, password: form.password })
  } catch (error) {
    errorMessage.value = error instanceof ApiClientError || error instanceof Error ? error.message : '登录请求失败，请重试'
    submitting.value = false
    return
  }
  syncRememberedPassword()
  const redirect = loginRedirect()
  try {
    await router.replace(redirect)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    if (/Failed to fetch dynamically imported module|Importing a module script failed|error loading dynamically imported module|Loading chunk .+ failed|Unable to preload CSS/i.test(message)) {
      const target = new URL(appPath(redirect), window.location.origin)
      if (!target.searchParams.has('__app_reload')) {
        target.searchParams.set('__app_reload', String(Date.now()))
        window.location.replace(target.href)
        return
      }
    }
    errorMessage.value = '已登录，但页面加载失败，请重新打开程序。'
  } finally {
    submitting.value = false
  }
}

function loginRedirect() {
  const requested = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  try {
    const target = new URL(requested || DEFAULT_AUTHENTICATED_PATH, window.location.origin)
    if (target.origin === window.location.origin && target.pathname !== '/login') return `${target.pathname}${target.search}${target.hash}`
  } catch { /* Invalid redirects fall back to the authenticated home page. */ }
  return DEFAULT_AUTHENTICATED_PATH
}

function syncRememberedPassword() {
  try {
    if (!rememberPassword.value) {
      localStorage.removeItem(rememberedPasswordKey)
      return
    }
    localStorage.setItem(
      rememberedPasswordKey,
      JSON.stringify({
        username: form.username,
        password: form.password
      })
    )
  } catch {
    rememberPassword.value = false
  }
}

function readRememberedPassword() {
  try {
    const raw = localStorage.getItem(rememberedPasswordKey)
    if (!raw) {
      return null
    }
    const value = JSON.parse(raw) as { username?: unknown; password?: unknown }
    const username = typeof value.username === 'string' ? value.username : ''
    const password = typeof value.password === 'string' ? value.password : ''
    return username || password ? { username, password } : null
  } catch {
    try { localStorage.removeItem(rememberedPasswordKey) } catch { /* Remembering credentials is optional. */ }
    return null
  }
}
</script>
