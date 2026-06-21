<template>
  <div class="event-panel">
    <n-empty v-if="events.length === 0" description="暂无事件" />
    <ol v-else class="event-list">
      <li v-for="event in events" :key="event.id" class="event-item">
        <div class="event-main">
          <strong>{{ event.event_type }}</strong>
          <span v-if="event.agent_name">{{ event.agent_name }}</span>
        </div>
        <p class="event-summary">{{ summarize(event.event_type, event.payload) }}</p>
      </li>
    </ol>
  </div>
</template>

<script setup lang="ts">
import type { RunEvent } from '../../api/runs'

defineProps<{
  events: RunEvent[]
}>()

function summarize(eventType: string, payload: Record<string, unknown>) {
  if (eventType === 'report_section_streamed') {
    const section = typeof payload.section === 'string' ? payload.section : 'unknown'
    const content = typeof payload.content_markdown === 'string' ? payload.content_markdown.trim() : ''
    const length = content.length
    // 中文注释：事件流只展示摘要，详细正文统一放到右侧报告区实时刷新。
    return `${section} 正在生成中，已接收 ${length} 个字符。`
  }

  const compactPayload = { ...payload }
  if (typeof compactPayload.content_markdown === 'string') {
    compactPayload.content_markdown = `${compactPayload.content_markdown.slice(0, 80)}...`
  }
  return JSON.stringify(compactPayload, null, 2)
}
</script>

<style scoped>
.event-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.event-item {
  padding: 12px;
  border: 1px solid #dde5f2;
  border-radius: 8px;
  background: #fbfcfe;
}

.event-main {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.event-main span {
  color: #667085;
}

.event-summary {
  margin: 8px 0 0;
  white-space: pre-wrap;
  color: #4b5565;
}
</style>
