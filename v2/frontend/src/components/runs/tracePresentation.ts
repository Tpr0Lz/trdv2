export function traceStatusType(status: string) {
  const typeByStatus: Record<string, 'default' | 'error' | 'info' | 'success' | 'warning'> = {
    completed: 'success',
    running: 'info',
    paused: 'warning',
    failed: 'error',
    cancelled: 'error',
    info: 'default'
  }
  return typeByStatus[status] ?? 'default'
}

export function traceKindLabel(kind: string) {
  const labelByKind: Record<string, string> = {
    run_lifecycle: '运行',
    agent_execution: 'Agent 执行',
    rag_evidence: 'RAG 证据',
    report_generation: '报告生成',
    tool_call: '工具调用',
    metric: '指标'
  }
  return labelByKind[kind] ?? kind
}
