import test from 'node:test'
import assert from 'node:assert/strict'
import { splitReportCitations } from './reportCitations.ts'

test('splitReportCitations separates citation tokens from plain text', () => {
  const parts = splitReportCitations('Macro pressure is elevated [E1], while breadth improved [E12].')

  assert.deepEqual(parts, [
    { text: 'Macro pressure is elevated ', citationKey: null },
    { text: '[E1]', citationKey: 'E1' },
    { text: ', while breadth improved ', citationKey: null },
    { text: '[E12]', citationKey: 'E12' },
    { text: '.', citationKey: null }
  ])
})

test('splitReportCitations preserves text without citations', () => {
  assert.deepEqual(splitReportCitations('No citations yet.'), [
    { text: 'No citations yet.', citationKey: null }
  ])
})
