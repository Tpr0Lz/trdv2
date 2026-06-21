<template>
  <div class="trace-panel">
    <n-empty v-if="items.length === 0" description="暂无 Agent 轨迹" />
    <n-timeline v-else>
      <n-timeline-item
        v-for="item in items"
        :key="item.id"
        :type="traceStatusType(item.status)"
        :title="item.title"
        :content="item.summary"
        :time="new Date(item.created_at).toLocaleString()"
      >
        <div class="trace-meta">
          <n-tag size="small">{{ traceKindLabel(item.kind) }}</n-tag>
          <n-tag v-if="item.agent_name" size="small" type="info">{{ item.agent_name }}</n-tag>
          <template v-if="citationKeys(item).length">
            <n-tag v-for="key in citationKeys(item)" :key="key" size="small" type="success">
              {{ key }}
            </n-tag>
          </template>
        </div>
      </n-timeline-item>
    </n-timeline>
  </div>
</template>

<script setup lang="ts">
import type { RunTraceItem } from '../../api/runs'
import { traceKindLabel, traceStatusType } from './tracePresentation'

defineProps<{
  items: RunTraceItem[]
}>()

function citationKeys(item: RunTraceItem): string[] {
  const value = item.metadata.citation_keys
  return Array.isArray(value) ? value.filter((key): key is string => typeof key === 'string') : []
}
</script>

<style scoped>
.trace-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}
</style>
