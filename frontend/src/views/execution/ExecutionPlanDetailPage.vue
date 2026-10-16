<template>
  <ExecutionPlanDetailWorkspace :plan-id="planId" @back="goBack" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ExecutionPlanDetailWorkspace from '../../components/execution/ExecutionPlanDetailWorkspace.vue'

const route = useRoute()
const router = useRouter()
const planId = computed(() => Number(route.params.planId || 0))

function goBack() {
  void router.push('/execution/plans')
}
</script>
