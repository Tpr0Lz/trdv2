import test from 'node:test'
import assert from 'node:assert/strict'
import { traceStatusType, traceKindLabel } from './tracePresentation.ts'

test('traceStatusType maps backend statuses to Naive UI tag types', () => {
  assert.equal(traceStatusType('completed'), 'success')
  assert.equal(traceStatusType('running'), 'info')
  assert.equal(traceStatusType('paused'), 'warning')
  assert.equal(traceStatusType('failed'), 'error')
  assert.equal(traceStatusType('cancelled'), 'error')
  assert.equal(traceStatusType('unknown'), 'default')
})

test('traceKindLabel maps trace kinds to readable labels', () => {
  assert.equal(traceKindLabel('rag_evidence'), 'RAG 证据')
  assert.equal(traceKindLabel('agent_execution'), 'Agent 执行')
  assert.equal(traceKindLabel('report_generation'), '报告生成')
})
