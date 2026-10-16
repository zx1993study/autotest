<template>
  <section class="page web-function-page">
    <header class="function-heading"><button type="button" title="返回页面管理" aria-label="返回页面管理" @click="router.push('/web/pages')"><ArrowLeft :size="18" /></button><div><nav><RouterLink to="/web/pages">页面管理</RouterLink><span>/</span><span>页面功能</span></nav><h2>{{ page?.name || '页面功能' }}</h2><code>{{ page?.data.route }}</code></div><div class="heading-actions"><button type="button" :disabled="discoveryLoading || !page || (!page.data.canonical_feature_id && !features.length)" @click="discoverPage"><Sparkles :size="16" />AI 发现</button><button type="button" :disabled="!page" @click="editing = null; editorVisible = true"><Plus :size="16" />添加功能</button></div></header>
    <div class="toolbar function-filters"><input v-model="keyword" type="search" placeholder="搜索功能名称" aria-label="搜索功能名称" @keyup.enter="search" /><select v-model="type" aria-label="业务类型"><option value="">全部类型</option><option v-for="(label, key) in types" :key="key" :value="key">{{ label }}</option></select><select v-model="scriptState" aria-label="脚本状态"><option value="">全部脚本状态</option><option value="verified">已验证</option><option value="draft">待验证</option><option value="missing">未生成</option><option value="legacy">历史脚本</option></select><button type="button" :disabled="loading" @click="search"><Search :size="15" />查询</button><button type="button" title="刷新" aria-label="刷新" :disabled="loading" @click="load"><RefreshCw :size="15" /></button></div>
    <p v-if="error || discoveryError" class="error" role="alert">{{ error || discoveryError }}</p>
    <div class="table-wrap"><table class="function-table"><colgroup><col class="name-col" /><col style="width:85px" /><col style="width:95px" /><col style="width:65px" /><col style="width:65px" /><col style="width:110px" /><col style="width:260px" /></colgroup><thead><tr><th>功能名称</th><th>业务类型</th><th>脚本状态</th><th>参数</th><th>用例</th><th>更新时间</th><th>操作</th></tr></thead><tbody>
      <tr v-for="feature in features" :key="feature.id"><td><button class="name-link" type="button" @click="detail(feature)">{{ feature.name }}</button><small v-if="feature.data.discovery_proposal" class="proposal">有待确认发现结果</small></td><td>{{ types[feature.data.feature_type] || '其他' }}</td><td><span class="state" :class="feature.script_status">{{ states[feature.script_status || 'missing'] }}</span></td><td>{{ feature.parameter_count || 0 }}</td><td>{{ feature.case_count }}</td><td>{{ date(feature.updated_at) }}</td><td><div class="row-actions"><button type="button" @click="detail(feature)">详情</button><button type="button" title="AI 发现" aria-label="AI 发现" @click="discover(feature)"><Sparkles :size="15" /></button><button type="button" title="编辑功能" aria-label="编辑功能" @click="editing = feature; editorVisible = true"><Pencil :size="15" /></button><button type="button" title="删除功能" aria-label="删除功能" @click="deleting = feature"><Trash2 :size="15" /></button></div></td></tr>
      <tr v-if="!features.length"><td colspan="7" class="empty">{{ loading ? '加载中' : error ? '加载失败' : '暂无匹配的功能' }}</td></tr>
    </tbody></table></div>
    <CommonPagination :page="currentPage" :page-size="pageSize" :total="total" :loading="loading" @change="paginate" />
    <WebFeatureFormDialog :visible="editorVisible" :group-id="groupId" :project-id="Number(page?.project_id || 0)" :feature="editing" @close="editorVisible = false" @saved="load" />
    <WebVisionDiscoveryDialog :visible="discoveryVisible" :project-id="Number(page?.project_id || 0)" :feature="discoveryFeature" @close="discoveryVisible = false" @completed="load" />
    <Teleport to="body"><div v-if="deleting" class="modal-backdrop" @click.self="deleting = null"><section class="modal-panel confirm-panel" role="dialog" aria-modal="true"><h3>删除功能</h3><p>删除「{{ deleting.name }}」及关联输入用例、脚本配置？执行记录将保留。</p><p v-if="deleteError" class="error">{{ deleteError }}</p><footer class="modal-actions"><button type="button" :disabled="deletingBusy" @click="deleting = null">取消</button><button type="button" :disabled="deletingBusy" @click="remove">删除</button></footer></section></div></Teleport>
  </section>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ArrowLeft, Pencil, Plus, RefreshCw, Search, Sparkles, Trash2 } from 'lucide-vue-next'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import CommonPagination from '../../components/common/CommonPagination.vue'
import WebFeatureFormDialog from '../../components/web-testing/WebFeatureFormDialog.vue'
import WebVisionDiscoveryDialog from '../../components/web-testing/WebVisionDiscoveryDialog.vue'
import { getWebPageGroup, listWebPageFeatures } from '../../services/web-page.service'
import { deleteWebFeature, getWebFeature } from '../../services/web-feature.service'
import { pageTabKey, usePageTabsStore } from '../../store/page-tabs'
import type { WebPageFeature, WebPageGroup } from '../../types/web-page'
import { useLatestRequest } from '../../composables/useLatestRequest'
const route = useRoute(), router = useRouter(), groupId = Number(route.params.pageId)
const page = ref<WebPageGroup | null>(null), features = ref<WebPageFeature[]>([]), keyword = ref(''), type = ref(''), scriptState = ref(''), total = ref(0)
const { loading, error, run: loadRequest } = useLatestRequest()
const { loading: discoveryLoading, error: discoveryError, run: loadDiscovery } = useLatestRequest()
const editorVisible = ref(false), editing = ref<WebPageFeature | null>(null), discoveryVisible = ref(false), discoveryFeature = ref<WebPageFeature | null>(null)
const deleting = ref<WebPageFeature | null>(null), deletingBusy = ref(false), deleteError = ref(''), currentPage = ref(1), pageSize = ref(20)
const types: Record<string,string> = { page: '页面', login: '登录', query: '查询', add: '新增', edit: '编辑', delete: '删除', detail: '详情', import: '导入', export: '导出', audit: '审核', submit: '提交', other: '其他' }
const states: Record<string,string> = { verified: '已验证', draft: '待验证', missing: '未生成', legacy: '历史脚本' }
onMounted(() => { usePageTabsStore().setTitle(pageTabKey(route), '页面功能'); void load() })
async function load() {
  features.value = []
  await loadRequest(async signal => {
    const [group, result] = await Promise.all([
      page.value ? Promise.resolve(page.value) : getWebPageGroup(groupId),
      listWebPageFeatures(groupId, { page: currentPage.value, pageSize: pageSize.value,
        keyword: keyword.value.trim() || undefined, feature_type: type.value || undefined,
        script_status: scriptState.value || undefined }, signal)
    ])
    return { group, result }
  }, ({ group, result }) => {
    page.value = group; features.value = result.items; total.value = result.total
  })
}
function detail(feature: WebPageFeature) { router.push(`/web/pages/${groupId}/features/${feature.id}`) }
function discover(feature?: WebPageFeature) { if (feature) { discoveryFeature.value = feature; discoveryVisible.value = true } }
async function discoverPage() {
  const canonicalId = Number(page.value?.data.canonical_feature_id || 0)
  const target = features.value.find(feature => feature.id === canonicalId)
  if (target || !canonicalId) { discover(target || features.value[0]); return }
  await loadDiscovery(() => getWebFeature(canonicalId), result => discover(result.feature))
}
function search() { currentPage.value = 1; void load() }
function paginate(page: number, size: number) { currentPage.value = page; pageSize.value = size; void load() }
function date(value?: string) { return value ? value.replace('T', ' ').slice(0, 16) : '-' }
async function remove() { if (!deleting.value) return; deletingBusy.value = true; deleteError.value = ''; try { await deleteWebFeature(deleting.value.id); deleting.value = null; if (features.value.length === 1 && currentPage.value > 1) currentPage.value -= 1; await load() } catch (e) { deleteError.value = e instanceof Error ? e.message : '删除失败' } finally { deletingBusy.value = false } }
</script>
<style scoped>
.web-function-page { grid-template-columns:minmax(0,1fr); }
.web-function-page > * { min-width:0; }
.heading-actions { flex-wrap:wrap; }
.web-function-page { display:grid; gap:18px; min-width:0; } .function-heading { display:flex; align-items:flex-start; gap:12px; padding-bottom:16px; border-bottom:1px solid #e2e8f0; } .function-heading h2 { font-size:20px; margin:8px 0; } nav { display:flex; gap:8px; font-size:12px; color:#667085; } code { font-size:12px; overflow-wrap:anywhere; } .heading-actions { display:flex; gap:8px; margin-left:auto; } button { display:inline-flex; align-items:center; justify-content:center; gap:6px; } .function-filters { flex-wrap:wrap; } .function-filters input { flex:1; max-width:440px; min-width:160px; } .function-filters select { width:140px; } .function-table { min-width:780px; table-layout:fixed; } .name-col { width:auto; } .name-link { border:0; background:none; padding:0; text-align:left; color:#0b6475; justify-content:flex-start; overflow-wrap:anywhere; } td { overflow-wrap:anywhere; } small.proposal { display:block; color:#947000; margin-top:5px; font-size:11px; } .state { font-size:12px; color:#667085; } .state.verified { color:#16804a; } .state.draft { color:#9a6700; } .empty { text-align:center; padding:48px 12px; color:#667085; } .error { color:#b42318; } .confirm-panel { padding:20px; width:min(460px,calc(100vw - 24px)); } @media(max-width:700px) { .function-heading { flex-wrap:wrap; } .heading-actions { margin-left:0; width:100%; } .function-filters input { max-width:none; flex-basis:100%; } }
</style>
