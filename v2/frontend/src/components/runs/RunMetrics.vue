<template>
  <n-card title="运行指标" class="metrics-card">
    <n-empty v-if="!metrics" description="暂无指标" />
    <div v-else class="metrics-grid">
      <div class="metric">
        <span>LLM 调用次数</span>
        <strong>{{ metrics.llm_calls }}</strong>
      </div>
      <div class="metric">
        <span>工具调用次数</span>
        <strong>{{ metrics.tool_calls }}</strong>
      </div>
      <div class="metric">
        <span>输入 Tokens</span>
        <strong>{{ metrics.tokens_in }}</strong>
      </div>
      <div class="metric">
        <span>输出 Tokens</span>
        <strong>{{ metrics.tokens_out }}</strong>
      </div>
      <div class="metric">
        <span>耗时</span>
        <strong>{{ metrics.elapsed_seconds }}s</strong>
      </div>
      <div class="metric">
        <span>更新时间</span>
        <strong>{{ updatedAt }}</strong>
      </div>
    </div>
    <div v-if="wallTimeItems.length" class="wall-times">
      <span>分析师耗时</span>
      <n-tag v-for="item in wallTimeItems" :key="item.name" size="small">
        {{ item.name }} · {{ item.value }}s
      </n-tag>
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { RunMetric } from '../../api/runs'

const props = defineProps<{
  metrics: RunMetric | null
}>()

const updatedAt = computed(() => {
  if (!props.metrics?.updated_at) return '等待中'
  return new Date(props.metrics.updated_at).toLocaleString()
})

const wallTimeItems = computed(() => {
  if (!props.metrics) return []
  return Object.entries(props.metrics.analyst_wall_times).map(([name, value]) => ({
    name,
    value
  }))
})
</script>

<style scoped>
.metrics-card {
  height: 100%;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.metric {
  min-height: 74px;
  padding: 12px;
  border: 1px solid #dde5f2;
  border-radius: 8px;
  background: #fbfcfe;
}

.metric span,
.wall-times > span {
  display: block;
  color: #667085;
  font-size: 12px;
}

.metric strong {
  display: block;
  margin-top: 8px;
  color: #172033;
  font-size: 22px;
}

.wall-times {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.wall-times > span {
  flex-basis: 100%;
}
</style>
