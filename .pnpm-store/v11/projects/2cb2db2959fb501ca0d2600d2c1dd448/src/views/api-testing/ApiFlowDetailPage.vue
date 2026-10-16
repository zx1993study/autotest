<template><ApiFlowWorkspace :key="flowId" :flow-id="flowId" /></template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import ApiFlowWorkspace from '../../components/api-flow/ApiFlowWorkspace.vue'
const route = useRoute()
const flowId = computed(() => Number(route.params.flowId))
</script>
