<template>
  <div class="tool-panel">
    <n-empty v-if="toolItems.length === 0" description="暂无工具调用轨迹" />
    <n-timeline v-else>
      <n-timeline-item
        v-for="item in toolItems"
        :key="item.id"
        :type="traceStatusType(item.status)"
        :title="toolTitle(item)"
        :content="item.summary"
        :time="new Date(item.created_at).toLocaleString()"
      >
        <div class="tool-meta">
          <n-tag v-if="item.agent_name" size="small" type="info">{{ item.agent_name }}</n-tag>
          <n-tag size="small">{{ item.event_type }}</n-tag>
        </div>
      </n-timeline-item>
    </n-timeline>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { RunTraceItem } from '../../api/runs'
import { traceStatusType } from './tracePresentation'

const props = defineProps<{
  items: RunTraceItem[]
}>()

const toolItems = computed(() => props.items.filter((item) => item.kind === 'tool_call'))

function toolTitle(item: RunTraceItem) {
  // 中文注释：优先展示真实工具名，缺失时回退到 trace 标题。
  return typeof item.metadata.tool_name === 'string' ? item.metadata.tool_name : item.title
}
</script>

<style scoped>
.tool-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}
</style>
