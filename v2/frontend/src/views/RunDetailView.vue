<template>
  <app-shell title="运行详情" subtitle="查看任务状态、实时事件和最终报告">
    <n-spin :show="runs.loading">
      <div v-if="runs.current" class="detail-grid">
        <n-card class="detail-card">
          <template #header>
            <div class="detail-header">
              <span>{{ runs.current.ticker }} · {{ runs.current.analysis_date }}</span>
              <run-status-tag :status="runs.current.status" />
            </div>
          </template>
          <template #header-extra>
            <n-space>
              <n-button v-if="canResume" size="small" type="primary" @click="handleResume">
                恢复
              </n-button>
              <n-button v-if="canPause" size="small" secondary type="warning" @click="handlePause">
                暂停
              </n-button>
              <n-button v-if="canCancel" size="small" secondary type="warning" @click="handleCancel">
                取消
              </n-button>
            </n-space>
          </template>
          <n-alert v-if="runs.current.status_reason" type="warning" class="status-reason">
            {{ runs.current.status_reason }}
          </n-alert>
          <n-descriptions bordered :column="1">
            <n-descriptions-item label="运行 ID">{{ runs.current.id }}</n-descriptions-item>
            <n-descriptions-item label="资产类型">{{ runs.current.asset_type }}</n-descriptions-item>
            <n-descriptions-item label="Checkpoint 线程">
              {{ runs.current.checkpoint_thread_id }}
            </n-descriptions-item>
            <n-descriptions-item label="参与分析师">
              {{ runs.current.selected_analysts.join(', ') }}
            </n-descriptions-item>
            <n-descriptions-item label="模型供应商">
              {{ runs.current.config_snapshot.llm_provider }}
            </n-descriptions-item>
            <n-descriptions-item label="模型配置">
              {{ runs.current.config_snapshot.deep_think_llm }} /
              {{ runs.current.config_snapshot.quick_think_llm }}
            </n-descriptions-item>
          </n-descriptions>
        </n-card>
        <run-metrics :metrics="runs.metrics" />
        <run-quality-panel :quality="runs.quality ?? null" />
      </div>
      <n-collapse v-model:expanded-names="expandedSections" class="run-sections">
        <n-collapse-item title="运行报告" name="reports">
          <report-tabs
            :run="runs.current"
            :reports="runs.reports"
            :streaming-reports="runs.streamingReports"
            @select-citation="handleSelectCitation"
          />
        </n-collapse-item>
        <n-collapse-item title="使用证据" name="evidence">
          <evidence-used :items="runs.evidence" :active-citation-key="activeCitationKey" />
        </n-collapse-item>
        <n-collapse-item title="工具调用轨迹" name="tools">
          <tool-call-trace :items="runs.trace" />
        </n-collapse-item>
        <n-collapse-item title="Agent 轨迹" name="trace">
          <agent-trace-timeline :items="runs.trace" />
        </n-collapse-item>
        <n-collapse-item title="事件流" name="events">
          <event-stream :events="runs.events" />
        </n-collapse-item>
      </n-collapse>
    </n-spin>
  </app-shell>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onBeforeUnmount, onMounted } from 'vue'
import { useRoute } from 'vue-router'

import AppShell from '../components/layout/AppShell.vue'
import AgentTraceTimeline from '../components/runs/AgentTraceTimeline.vue'
import EvidenceUsed from '../components/runs/EvidenceUsed.vue'
import EventStream from '../components/runs/EventStream.vue'
import ReportTabs from '../components/runs/ReportTabs.vue'
import RunMetrics from '../components/runs/RunMetrics.vue'
import RunQualityPanel from '../components/runs/RunQualityPanel.vue'
import RunStatusTag from '../components/runs/RunStatusTag.vue'
import ToolCallTrace from '../components/runs/ToolCallTrace.vue'
import type { RunEvent } from '../api/runs'
import { openRunEventSource } from '../sse/runEvents'
import { useRunsStore } from '../stores/runs'

const route = useRoute()
const runs = useRunsStore()
let source: EventSource | null = null
const runId = computed(() => String(route.params.runId))
const activeCitationKey = ref<string | null>(null)
// 中文注释：报告默认展开，其它高频更新区块默认收起，减少流式时页面高度变化。
const expandedSections = ref<string[]>(['reports'])

const canResume = computed(() => {
  return (
    runs.current?.status === 'paused' ||
    runs.current?.status === 'interrupted' ||
    runs.current?.status === 'failed'
  )
})

const canPause = computed(() => {
  return runs.current?.status === 'queued' || runs.current?.status === 'running'
})

const canCancel = computed(() => {
  return (
    runs.current?.status === 'queued' ||
    runs.current?.status === 'running' ||
    runs.current?.status === 'paused'
  )
})

const terminalEvents = new Set([
  'run_paused',
  'run_interrupted',
  'run_completed',
  'run_failed',
  'run_cancelled'
])

onMounted(async () => {
  await runs.fetchDetail(runId.value)
  // 中文注释：详情已加载完整历史，SSE 只接收新事件，避免旧状态回放覆盖当前状态。
  source = openRunEventSource(runId.value, handleStreamEvent, runs.lastLoadedEventId)
})

onBeforeUnmount(() => {
  source?.close()
})

async function handleResume() {
  await runs.resume(runId.value)
}

async function handlePause() {
  await runs.pause(runId.value)
}

async function handleCancel() {
  await runs.cancel(runId.value)
}

function handleSelectCitation(citationKey: string) {
  activeCitationKey.value = citationKey
  // 中文注释：用户点击报告引用时，只定位证据列表，不改变当前报告 tab。
  document.querySelector(`[data-citation-key="${citationKey}"]`)?.scrollIntoView({
    behavior: 'smooth',
    block: 'center'
  })
}

function handleStreamEvent(event: RunEvent) {
  runs.upsertEvent(event)
  if (terminalEvents.has(event.event_type)) {
    // 中文注释：终态事件后刷新完整 run 详情，补齐 status_reason 和时间字段。
    void runs.fetchDetail(runId.value)
    return
  }
  if (
    event.event_type === 'agent_started' ||
    event.event_type === 'tool_started' ||
    event.event_type === 'tool_completed' ||
    event.event_type === 'tool_failed' ||
    event.event_type === 'report_section_updated' ||
    event.event_type === 'metric_updated'
  ) {
    runs.fetchArtifacts(runId.value)
  }
}
</script>

<style scoped>
.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(300px, 0.8fr) minmax(300px, 0.8fr);
  gap: 18px;
  max-width: 1120px;
}

.detail-card {
  min-width: 0;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.status-reason {
  margin-bottom: 14px;
}

.run-sections {
  max-width: 1120px;
  margin-top: 18px;
}

.run-sections :deep(.n-collapse-item) {
  border: 1px solid #dde5f2;
  border-radius: 10px;
  background: #ffffff;
}

.run-sections :deep(.n-collapse-item + .n-collapse-item) {
  margin-top: 12px;
}

.run-sections :deep(.n-collapse-item__header) {
  padding: 14px 18px;
}

.run-sections :deep(.n-collapse-item__content-inner) {
  padding: 0 18px 18px;
}

@media (max-width: 920px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
