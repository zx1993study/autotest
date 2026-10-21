<template>
  <section class="mini-workspace">
    <header><h2>小程序测试</h2><button :disabled="busy" title="刷新" aria-label="刷新" @click="load"><RefreshCw :size="17" /></button></header>
    <div class="mini-toolbar">
      <ProjectFilterSelect v-model="projectId" :include-all="false" @ready="ready = true" />
      <input v-model="keyword" aria-label="搜索用例" placeholder="搜索名称或 ID" type="search" />
      <select v-model="category" aria-label="用例类别"><option value="">全部类别</option><option v-for="(label, key) in sourceCategories" :key="key" :value="key">{{ label }}</option></select>
      <button :disabled="busy || !projectId" @click="fileInput?.click()"><Upload :size="16" />导入测试包</button>
      <input ref="fileInput" hidden type="file" accept="application/json,.json" @change="onFile" />
    </div>
    <p v-if="error" role="alert" class="mini-error">{{ error }}</p><p v-if="message" role="status">{{ message }}</p>
    <div class="mini-toolbar">
      <label class="mini-check"><input type="checkbox" :checked="allSelected" @change="selectAll" />当前筛选 {{ filtered.length }} 个</label>
      <span>已选 {{ selected.length }}</span>
      <select v-model="platform" aria-label="执行平台"><option value="mp-weixin">微信小程序</option><option value="h5">同源 H5</option></select>
      <button :disabled="busy || !selected.length" @click="execute"><Play :size="16" />执行选中</button>
    </div>
    <div class="mini-table-scroll"><table><thead><tr><th></th><th>ID</th><th>用例名称</th><th>类别</th><th>自动化</th><th>业务流程</th><th></th></tr></thead>
      <tbody><tr v-for="row in visible" :key="row.id"><td><input v-model="selected" type="checkbox" :value="row.id" :aria-label="`选择 ${row.name}`" /></td><td>{{ row.id }}</td><td>{{ row.name }}</td><td>{{ sourceCategories[row.data.category || ''] }}</td><td>{{ row.data.definition?.automation === 'scripted' ? '脚本' : '待人工/数据' }}</td><td>{{ row.data.api_business ? `#${row.data.api_business.flow_id} / #${row.data.api_business.scenario_id}` : '-' }}</td><td><button @click="detail = row">详情</button></td></tr>
      <tr v-if="!visible.length"><td colspan="7">{{ busy ? '加载中' : '暂无源码测试用例' }}</td></tr></tbody></table></div>
    <footer><button :disabled="page === 1" title="上一页" aria-label="上一页" @click="page--"><ChevronLeft :size="16" /></button><span>{{ page }} / {{ pages }}</span><button :disabled="page >= pages" title="下一页" aria-label="下一页" @click="page++"><ChevronRight :size="16" /></button></footer>
    <h3>运行记录</h3>
    <div class="mini-table-scroll"><table><thead><tr><th>批次</th><th>平台</th><th>用例数</th><th>结果</th><th>状态</th><th></th></tr></thead><tbody>
      <tr v-for="run in runs" :key="run.id"><td>#{{ run.id }}</td><td>{{ run.data.platform }}</td><td>{{ run.data.case_count }}</td><td>通过 {{ run.data.counts?.success || 0 }} · 失败 {{ run.data.counts?.failed || 0 }} · 阻塞 {{ run.data.counts?.blocked || 0 }}</td><td>{{ sourceStatuses[run.status] || run.status }}</td><td><button @click="showRun(run.id)">查看结果</button></td></tr>
      <tr v-if="!runs.length"><td colspan="6">暂无运行记录</td></tr>
    </tbody></table></div>
    <MiniappSourceCaseDialog v-if="detail" :item="detail" @close="detail = null" @saved="replaceCase" />
    <MiniappSourceRunDialog v-if="runDetail" :run="runDetail" @close="closeRun" />
  </section>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { ChevronLeft, ChevronRight, Play, RefreshCw, Upload } from 'lucide-vue-next'
import ProjectFilterSelect from '../filters/ProjectFilterSelect.vue'
import MiniappSourceCaseDialog from './MiniappSourceCaseDialog.vue'
import MiniappSourceRunDialog from './MiniappSourceRunDialog.vue'
import { useMiniappSource } from '../../composables/useMiniappSource'
import { sourceCategories, sourceStatuses, type SourceCase } from '../../types/miniapp-source'
import '../../styles/miniapp-source.css'
const { projectId, ready, cases, runs, selected, category, keyword, platform, busy, error, message,
  detail, runDetail, page, pages, filtered, visible, load, importFile, execute, showRun, closeRun } = useMiniappSource()
const fileInput = ref<HTMLInputElement>()
const allSelected = computed(() => filtered.value.length > 0 && filtered.value.every(row => selected.value.includes(row.id)))
function selectAll() { selected.value = allSelected.value ? [] : filtered.value.map(row => row.id) }
function onFile(event: Event) {
  const input = event.target as HTMLInputElement
  void importFile(input.files?.[0]); input.value = ''
}
function replaceCase(item: SourceCase) {
  cases.value = cases.value.map(row => row.id === item.id ? item : row)
  detail.value = item
}
</script>
