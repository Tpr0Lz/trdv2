<template>
  <n-tag :type="type" round>{{ label }}</n-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: string
}>()

const type = computed(() => {
  if (props.status === 'completed') return 'success'
  if (props.status === 'failed' || props.status === 'interrupted') return 'error'
  if (props.status === 'running') return 'info'
  if (props.status === 'queued' || props.status === 'paused') return 'warning'
  return 'default'
})

const label = computed(() => {
  const labelByStatus: Record<string, string> = {
    completed: '已完成',
    failed: '失败',
    interrupted: '中断',
    running: '运行中',
    queued: '排队中',
    paused: '已暂停',
    cancelled: '已取消'
  }
  return labelByStatus[props.status] ?? props.status
})
</script>
