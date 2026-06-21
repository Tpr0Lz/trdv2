import { defineStore } from 'pinia'

import * as runsApi from '../api/runs'
import type {
  Run,
  RunCreatePayload,
  RunEvent,
  RunEvidence,
  RunMetric,
  RunQuality,
  RunReport,
  RunTraceItem,
  StreamingReport
} from '../api/runs'

interface RunsState {
  items: Run[]
  current: Run | null
  events: RunEvent[]
  trace: RunTraceItem[]
  reports: RunReport[]
  evidence: RunEvidence[]
  streamingReports: Record<string, StreamingReport>
  metrics: RunMetric | null
  quality: RunQuality | null
  lastLoadedEventId: number | null
  loading: boolean
}

export const useRunsStore = defineStore('runs', {
  state: (): RunsState => ({
    items: [],
    current: null,
    events: [],
    trace: [],
    reports: [],
    evidence: [],
    streamingReports: {},
    metrics: null,
    quality: null,
    lastLoadedEventId: null,
    loading: false
  }),
  actions: {
    async create(payload: RunCreatePayload) {
      this.loading = true
      try {
        const run = await runsApi.createRun(payload)
        this.current = run
        this.items = [run, ...this.items.filter((item) => item.id !== run.id)]
        return run
      } finally {
        this.loading = false
      }
    },
    async fetchList() {
      this.loading = true
      try {
        this.items = await runsApi.listRuns()
      } finally {
        this.loading = false
      }
    },
    async fetchDetail(runId: string) {
      this.loading = true
      try {
        const [run, events, trace, reports, metrics, evidence, quality] = await Promise.all([
          runsApi.getRun(runId),
          runsApi.listRunEvents(runId),
          runsApi.listRunTrace(runId),
          runsApi.listRunReports(runId),
          runsApi.getRunMetrics(runId),
          runsApi.listRunEvidence(runId),
          runsApi.getRunQuality(runId)
        ])
        this.current = run
        this.events = filterVisibleEvents(events)
        this.trace = trace
        this.lastLoadedEventId = maxEventId(events)
        this.reports = reports
        this.evidence = evidence
        // 中文注释：详情页中途打开时，要把历史 stream 事件回放成当前报告区状态。
        this.streamingReports = rebuildStreamingReports(events, reports)
        this.metrics = metrics
        this.quality = quality
      } finally {
        this.loading = false
      }
    },
    async fetchArtifacts(runId: string) {
      const [trace, reports, metrics, evidence, quality] = await Promise.all([
        runsApi.listRunTrace(runId),
        runsApi.listRunReports(runId),
        runsApi.getRunMetrics(runId),
        runsApi.listRunEvidence(runId),
        runsApi.getRunQuality(runId)
      ])
      this.trace = trace
      this.reports = reports
      this.metrics = metrics
      this.evidence = evidence
      this.quality = quality
      this.streamingReports = stripFinalizedStreamingReports(this.streamingReports, reports)
    },
    async resume(runId: string) {
      const run = await runsApi.resumeRun(runId)
      this.applyRun(run)
      return run
    },
    async pause(runId: string) {
      const run = await runsApi.pauseRun(runId)
      this.applyRun(run)
      return run
    },
    async cancel(runId: string) {
      const run = await runsApi.cancelRun(runId)
      this.applyRun(run)
      return run
    },
    upsertEvent(event: RunEvent) {
      this.lastLoadedEventId = Math.max(this.lastLoadedEventId ?? 0, event.id)
      const exists = this.events.some((item) => item.id === event.id)
      if (!exists && event.event_type !== 'report_section_streamed') {
        this.events = [...this.events, event].sort((a, b) => a.id - b.id)
      }
      this.applyStreamingReportEvent(event)
      this.applyStatusEvent(event)
    },
    applyRun(run: Run) {
      this.current = run
      this.items = this.items.map((item) => (item.id === run.id ? run : item))
    },
    applyStatusEvent(event: RunEvent) {
      if (!this.current || this.current.id !== event.run_id) return
      const statusByEvent: Record<string, string> = {
        run_started: 'running',
        run_paused: 'paused',
        run_interrupted: 'interrupted',
        run_completed: 'completed',
        run_failed: 'failed',
        run_cancelled: 'cancelled'
      }
      const status = statusByEvent[event.event_type]
      if (status) {
        const statusReason = event.payload.error ?? event.payload.reason
        // 中文注释：SSE 事件先更新页面状态和失败原因，避免页面停留在旧状态。
        this.current = {
          ...this.current,
          status,
          status_reason:
            typeof statusReason === 'string' ? statusReason : this.current.status_reason
        }
      }
    },
    applyStreamingReportEvent(event: RunEvent) {
      if (event.event_type === 'report_section_streamed') {
        const section = typeof event.payload.section === 'string' ? event.payload.section : null
        if (!section) return
        this.streamingReports = {
          ...this.streamingReports,
          [section]: {
            section,
            title: typeof event.payload.title === 'string' ? event.payload.title : section,
            agent_name: event.agent_name,
            content_markdown:
              typeof event.payload.content_markdown === 'string' ? event.payload.content_markdown : '',
            updated_at: event.created_at
          }
        }
        return
      }
    }
  }
})

function rebuildStreamingReports(events: RunEvent[], reports: RunReport[]) {
  const streamingReports: Record<string, StreamingReport> = {}
  const finalizedSections = new Set(reports.map((report) => report.section))
  for (const event of events) {
    if (event.event_type !== 'report_section_streamed') {
      continue
    }
    const section = typeof event.payload.section === 'string' ? event.payload.section : null
    if (!section || finalizedSections.has(section)) {
      continue
    }
    streamingReports[section] = {
      section,
      title: typeof event.payload.title === 'string' ? event.payload.title : section,
      agent_name: event.agent_name,
      content_markdown:
        typeof event.payload.content_markdown === 'string' ? event.payload.content_markdown : '',
      updated_at: event.created_at
    }
  }
  return streamingReports
}

function stripFinalizedStreamingReports(
  streamingReports: Record<string, StreamingReport>,
  reports: RunReport[]
) {
  const finalizedSections = new Set(reports.map((report) => report.section))
  const next: Record<string, StreamingReport> = {}
  for (const [section, report] of Object.entries(streamingReports)) {
    if (!finalizedSections.has(section)) {
      next[section] = report
    }
  }
  return next
}

function filterVisibleEvents(events: RunEvent[]) {
  return events.filter((event) => event.event_type !== 'report_section_streamed')
}

function maxEventId(events: RunEvent[]) {
  return events.reduce<number | null>((maxId, event) => {
    return maxId == null ? event.id : Math.max(maxId, event.id)
  }, null)
}
