<template>
  <nav class="page-tabs" aria-label="已打开页面">
    <div ref="scrollRef" class="page-tabs-scroll" role="tablist">
      <div
        v-for="tabItem in tabs"
        :key="tabItem.key"
        class="page-tab"
        :class="{ active: tabItem.key === activeKey }"
        :data-tab-key="tabItem.key"
      >
        <button
          class="page-tab-label"
          type="button"
          role="tab"
          :aria-selected="tabItem.key === activeKey"
          :title="tabItem.title"
          @click="activateTab(tabItem)"
        >
          {{ tabItem.title }}
        </button>
        <button
          v-if="tabItem.closable"
          class="page-tab-close"
          type="button"
          :aria-label="`关闭 ${tabItem.title}`"
          :title="`关闭 ${tabItem.title}`"
          @click="removeTab(tabItem)"
        >
          &times;
        </button>
      </div>
    </div>

    <details ref="menuRef" class="page-tabs-menu">
      <summary aria-label="管理已打开页面" title="管理已打开页面">...</summary>
      <div class="page-tabs-menu-panel">
        <div class="mobile-page-list" aria-label="切换已打开页面">
          <button
            v-for="tabItem in tabs"
            :key="tabItem.key"
            type="button"
            :class="{ active: tabItem.key === activeKey }"
            @click="activateTabFromMenu(tabItem)"
          >
            {{ tabItem.title }}
          </button>
        </div>
        <button type="button" :disabled="!activeTab?.closable" @click="closeCurrent">关闭当前</button>
        <button type="button" :disabled="tabs.length <= 1" @click="closeOthers">关闭其他</button>
        <button type="button" :disabled="tabs.length <= 1" @click="closeAll">关闭全部</button>
      </div>
    </details>
  </nav>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { navigationGroups } from '../../constants/navigation'
import { DEFAULT_AUTHENTICATED_PATH } from '../../constants/routes'
import { pageTabKey, usePageTabsStore } from '../../store/page-tabs'
import type { OpenedPageTab } from '../../store/page-tabs'

const route = useRoute()
const router = useRouter()
const menuRef = ref<HTMLDetailsElement | null>(null)
const scrollRef = ref<HTMLElement | null>(null)
const pageTabsStore = usePageTabsStore()
const { tabs } = pageTabsStore

const activeKey = computed(() => pageTabKey(route))
const activeTab = computed(() => tabs.value.find(tabItem => tabItem.key === activeKey.value))

watch(
  () => route.fullPath,
  () => pageTabsStore.openRoute(route, routeTitle()),
  { immediate: true }
)

watch(
  () => activeTab.value?.title,
  title => {
    if (title) document.title = `${title} - 自动化测试软件`
  },
  { immediate: true }
)

watch(
  () => [activeKey.value, tabs.value.length],
  scrollActiveTabIntoView,
  { flush: 'post' }
)

onMounted(() => {
  pageTabsStore.pruneTabs(path => {
    const resolved = router.resolve(path)
    return resolved.path !== '/login'
      && resolved.matched.length > 0
      && !resolved.matched.some(record => Boolean(record.redirect))
  })
  pageTabsStore.openRoute(route, routeTitle())
  document.addEventListener('pointerdown', handleDocumentPointerDown)
})

onBeforeUnmount(() => document.removeEventListener('pointerdown', handleDocumentPointerDown))

async function activateTab(tabItem: OpenedPageTab) {
  if (tabItem.key !== activeKey.value) await router.push(tabItem.path)
}

async function activateTabFromMenu(tabItem: OpenedPageTab) {
  closeMenu()
  await activateTab(tabItem)
}

async function removeTab(tabItem: OpenedPageTab) {
  const wasActive = tabItem.key === activeKey.value
  const nextPath = pageTabsStore.closeTab(tabItem.key)
  if (wasActive && nextPath) await router.push(nextPath)
}

async function closeCurrent() {
  closeMenu()
  if (!activeTab.value) return
  await removeTab(activeTab.value)
}

function closeOthers() {
  closeMenu()
  pageTabsStore.closeOtherTabs(activeKey.value)
}

async function closeAll() {
  closeMenu()
  pageTabsStore.closeAllTabs()
  if (route.path !== DEFAULT_AUTHENTICATED_PATH) await router.push(DEFAULT_AUTHENTICATED_PATH)
}

function closeMenu() {
  menuRef.value?.removeAttribute('open')
}

function handleDocumentPointerDown(event: PointerEvent) {
  if (menuRef.value?.open && event.target instanceof Node && !menuRef.value.contains(event.target)) {
    closeMenu()
  }
}

async function scrollActiveTabIntoView() {
  await nextTick()
  const activeElement = Array.from(scrollRef.value?.children || [])
    .find(element => (element as HTMLElement).dataset.tabKey === activeKey.value)
  activeElement?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
}

function routeTitle() {
  const metaTitle = route.meta.title
  if (typeof metaTitle === 'string' && metaTitle) return metaTitle
  const menuItem = navigationGroups
    .flatMap(group => group.items)
    .filter(item => route.path === item.path || route.path.startsWith(`${item.path}/`))
    .sort((left, right) => right.path.length - left.path.length)[0]
  return menuItem?.label || '未命名页面'
}
</script>

<style scoped>
.page-tabs {
  display: flex;
  align-items: stretch;
  min-width: 0;
  flex: 1 1 auto;
  height: 42px;
  background: #ffffff;
  padding-left: var(--content-gutter, 28px);
}

.page-tabs-scroll {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  overflow-x: auto;
  scrollbar-width: thin;
}

.page-tab {
  display: flex;
  align-items: center;
  min-width: 112px;
  max-width: 250px;
  flex: 0 0 auto;
  border-right: 1px solid #e7ebf2;
  border-bottom: 2px solid transparent;
}

.page-tab.active {
  border-bottom-color: #0f6b7a;
  background: #f5fafb;
}

.page-tab-label,
.page-tab-close {
  border: 0;
  border-radius: 0;
  background: transparent;
  color: #536176;
}

.page-tab-label {
  min-width: 0;
  flex: 1 1 auto;
  overflow: hidden;
  padding: 0 8px 0 12px;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.page-tab.active .page-tab-label {
  color: #124e5a;
  font-weight: 700;
}

.page-tab-close {
  width: 30px;
  height: 30px;
  flex: 0 0 30px;
  padding: 0;
  font-size: 18px;
  line-height: 1;
}

.page-tab-close:hover {
  background: #e8eef3;
  color: #b42318;
}

.page-tabs-menu {
  position: relative;
  box-sizing: border-box;
  width: 44px;
  flex: 0 0 44px;
  border-left: 1px solid #e1e7ef;
  background: #ffffff;
}

.page-tabs-menu summary {
  display: grid;
  width: 100%;
  height: 40px;
  cursor: pointer;
  place-items: center;
  color: #445168;
  font-weight: 700;
  list-style: none;
}

.page-tabs-menu summary::-webkit-details-marker {
  display: none;
}

.page-tabs-menu-panel {
  position: absolute;
  z-index: 40;
  top: 44px;
  right: 8px;
  display: grid;
  width: 150px;
  border: 1px solid #d9e1ec;
  border-radius: 6px;
  background: #ffffff;
  padding: 6px;
  box-shadow: 0 10px 28px rgb(19 33 54 / 16%);
}

.page-tabs-menu-panel > button,
.mobile-page-list button {
  border: 0;
  background: transparent;
  color: #35435a;
  padding: 8px 10px;
  text-align: left;
}

.page-tabs-menu-panel button:hover:not(:disabled) {
  background: #edf5f6;
}

.page-tabs-menu-panel button:disabled {
  color: #a2adbc;
}

.mobile-page-list {
  display: none;
}

@media (max-width: 720px) {
  .page-tabs {
    padding-left: var(--content-gutter, 12px);
  }

  .page-tab {
    display: none;
    max-width: none;
    border-left: 1px solid #e7ebf2;
  }

  .page-tab.active {
    display: flex;
    min-width: 0;
    flex: 1 1 auto;
  }

  .page-tabs-menu-panel {
    right: 4px;
    width: min(280px, calc(100vw - 24px));
  }

  .mobile-page-list {
    display: grid;
    max-height: 260px;
    overflow-y: auto;
    margin-bottom: 5px;
    border-bottom: 1px solid #e2e7ef;
    padding-bottom: 5px;
  }

  .mobile-page-list button {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mobile-page-list button.active {
    color: #0f5f6d;
    font-weight: 700;
  }
}
</style>
