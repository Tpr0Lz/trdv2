import type { RunEvent } from '../api/runs'

export function openRunEventSource(
  runId: string,
  onEvent: (event: RunEvent) => void,
  afterEventId: number | null = null
): EventSource {
  const query = afterEventId == null ? '' : `?after_event_id=${encodeURIComponent(afterEventId)}`
  const source = new EventSource(`/api/runs/${runId}/stream${query}`, { withCredentials: true })
  source.onmessage = (message) => {
    onEvent(JSON.parse(message.data) as RunEvent)
  }
  const knownEvents = [
    'run_created',
    'run_started',
    'run_paused',
    'run_interrupted',
    'run_resumed',
    'run_completed',
    'run_failed',
    'run_cancelled',
    'agent_started',
    'agent_completed',
    'tool_call_started',
    'tool_call_completed',
    'tool_call_failed',
    'report_section_streamed',
    'report_section_updated',
    'checkpoint_saved',
    'metric_updated',
    'log_message'
  ]
  // 中文注释：SSE 会使用具名 event，这里统一解析成 RunEvent。
  for (const eventName of knownEvents) {
    source.addEventListener(eventName, (message) => {
      onEvent(JSON.parse((message as MessageEvent).data) as RunEvent)
    })
  }
  return source
}
