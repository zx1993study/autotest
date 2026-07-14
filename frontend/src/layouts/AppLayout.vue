<template>
  <div class="app-shell">
    <header class="mobile-topbar">
      <button
        class="menu-toggle"
        type="button"
        aria-label="打开菜单"
        :aria-expanded="sidebarOpen"
        @click="openSidebar"
      >
        ☰
      </button>
      <strong>自动化测试软件</strong>
    </header>

    <div v-if="sidebarOpen" class="sidebar-backdrop" @click="closeSidebar"></div>

    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <h1>自动化测试软件</h1>
      <nav>
        <section v-for="group in visibleMenus" :key="group.title">
          <button
            class="menu-group"
            :class="{ expanded: isGroupExpanded(group.title) }"
            type="button"
            @click="toggleGroup(group.title)"
          >
            <span>{{ group.title }}</span>
            <span class="menu-arrow">›</span>
          </button>
          <div v-if="isGroupExpanded(group.title)" class="submenu">
            <RouterLink
              v-for="item in group.items"
              :key="item.path"
              :to="item.path"
              @click="closeSidebar"
            >
              {{ item.label }}
            </RouterLink>
          </div>
        </section>
      </nav>
    </aside>

    <main class="content">
      <header class="content-topbar">
        <div>
          <span class="topbar-kicker">当前用户</span>
          <strong>{{ displayName }}</strong>
        </div>
        <button class="logout-button" type="button" @click="handleLogout">退出登录</button>
      </header>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { hiddenFeaturePrefixes, navigationGroups } from '../constants/navigation'
import { useAuthStore } from '../store/auth'
import { useUiStore } from '../store/ui'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const {
  sidebarOpen,
  openSidebar,
  closeSidebar,
  isGroupExpanded,
  toggleGroup,
  expandGroup
} = useUiStore()

const visibleMenus = computed(() =>
  navigationGroups
    .map(group => ({
      ...group,
      items: group.items.filter(
        item => !hiddenFeaturePrefixes.some(prefix => item.path.startsWith(prefix))
      )
    }))
    .filter(group => group.items.length > 0)
)

const activeGroupTitle = computed(
  () => visibleMenus.value.find(group => group.items.some(item => item.path === route.path))?.title
)

const displayName = computed(() => {
  const user = authStore.currentUser.value
  return user?.display_name || user?.username || '-'
})

async function handleLogout() {
  await authStore.logout()
  await router.replace('/login')
}

watch(
  activeGroupTitle,
  title => {
    if (title) {
      expandGroup(title)
    }
  },
  { immediate: true }
)
</script>
