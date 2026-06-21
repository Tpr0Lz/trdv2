import { http } from './http'

export interface RunCreatePayload {
  ticker: string
  analysis_date: string
  asset_type: string
  selected_analysts: string[]
  research_depth: number
  llm_provider: string
  deep_think_llm: string
  quick_think_llm: string
  output_language: string
}

export interface Run {
  id: string
  ticker: string
  analysis_date: string
  asset_type: string
  status: string
  status_reason: string | null
  selected_analysts: string[]
  config_snapshot: Record<string, unknown>
  checkpoint_thread_id: string
  created_at: string
  updated_at: string
}

export interface RunEvent {
  id: number
  run_id: string
  event_type: string
  agent_name: string | null
  sequence: number
  payload: Record<string, unknown>
  created_at: string
}

export interface RunTraceItem {
  id: string
  run_id: string
  order: number
  kind: string
  event_type: string
  agent_name: string | null
  title: string
  summary: string
  status: string
  created_at: string
  metadata: Record<string, unknown>
}

export interface StreamingReport {
  section: string
  title: string
  agent_name: string | null
  content_markdown: string
  updated_at: string
}

export interface RunReport {
  id: string
  run_id: string
  section: string
  title: string
  content_markdown: string
  version: number
  created_at: string
  updated_at: string
}

export interface RunMetric {
  run_id: string
  llm_calls: number
  tool_calls: number
  tokens_in: number
  tokens_out: number
  elapsed_seconds: number
  analyst_wall_times: Record<string, number>
  updated_at: string | null
}

export interface RunEvidence {
  id: string
  run_id: string
  agent_name: string
  query: string
  citation_key: string | null
  score: number
  excerpt: string
  source_id: string
  source_title: string
  source_type: string
  source_name: string
  published_at: string | null
  url: string | null
  created_at: string
}

export interface RunQualityCheck {
  id: string
  title: string
  status: string
  summary: string
  score_delta: number
  details: Record<string, unknown>
}

export interface RunQuality {
  run_id: string
  score: number
  status: string
  checks: RunQualityCheck[]
}

export async function createRun(payload: RunCreatePayload): Promise<Run> {
  const response = await http.post<Run>('/runs', payload)
  return response.data
}

export async function listRuns(): Promise<Run[]> {
  const response = await http.get<{ items: Run[] }>('/runs')
  return response.data.items
}

export async function getRun(runId: string): Promise<Run> {
  const response = await http.get<Run>(`/runs/${runId}`)
  return response.data
}

export async function listRunEvents(runId: string): Promise<RunEvent[]> {
  const response = await http.get<{ items: RunEvent[] }>(`/runs/${runId}/events`)
  return response.data.items
}

export async function listRunTrace(runId: string): Promise<RunTraceItem[]> {
  const response = await http.get<{ items: RunTraceItem[] }>(`/runs/${runId}/trace`)
  return response.data.items
}

export async function listRunReports(runId: string): Promise<RunReport[]> {
  const response = await http.get<{ items: RunReport[] }>(`/runs/${runId}/reports`)
  return response.data.items
}

export async function getRunMetrics(runId: string): Promise<RunMetric> {
  const response = await http.get<RunMetric>(`/runs/${runId}/metrics`)
  return response.data
}

export async function listRunEvidence(runId: string): Promise<RunEvidence[]> {
  const response = await http.get<{ items: RunEvidence[] }>(`/runs/${runId}/evidence`)
  return response.data.items
}

export async function getRunQuality(runId: string): Promise<RunQuality> {
  const response = await http.get<RunQuality>(`/runs/${runId}/quality`)
  return response.data
}

export async function resumeRun(runId: string): Promise<Run> {
  const response = await http.post<Run>(`/runs/${runId}/resume`)
  return response.data
}

export async function pauseRun(runId: string): Promise<Run> {
  const response = await http.post<Run>(`/runs/${runId}/pause`)
  return response.data
}

export async function cancelRun(runId: string): Promise<Run> {
  const response = await http.post<Run>(`/runs/${runId}/cancel`)
  return response.data
}
