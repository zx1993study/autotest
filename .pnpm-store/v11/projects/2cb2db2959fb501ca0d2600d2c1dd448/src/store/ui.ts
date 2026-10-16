import { readonly, ref } from 'vue'

const sidebarOpen = ref(false)
const expandedGroups = ref<Set<string>>(new Set())

function openSidebar() {
  sidebarOpen.value = true
}

function closeSidebar() {
  sidebarOpen.value = false
}

function isGroupExpanded(title: string) {
  return expandedGroups.value.has(title)
}

function toggleGroup(title: string) {
  const next = new Set(expandedGroups.value)
  if (next.has(title)) {
    next.delete(title)
  } else {
    next.add(title)
  }
  expandedGroups.value = next
}

function expandGroup(title: string) {
  if (expandedGroups.value.has(title)) {
    return
  }
  expandedGroups.value = new Set([...expandedGroups.value, title])
}

/** Singleton UI store for layout state shared across routed views. */
export function useUiStore() {
  return {
    sidebarOpen: readonly(sidebarOpen),
    expandedGroups: readonly(expandedGroups),
    openSidebar,
    closeSidebar,
    isGroupExpanded,
    toggleGroup,
    expandGroup
  }
}
