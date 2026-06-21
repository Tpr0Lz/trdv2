import test from 'node:test'
import assert from 'node:assert/strict'
import { buildRunReportTeams } from './reportTabsModel.ts'

test('buildRunReportTeams keeps original team order and agent order', () => {
  const run = {
    asset_type: 'stock',
    selected_analysts: ['market', 'social', 'news', 'fundamentals']
  }

  const teams = buildRunReportTeams(run, [])

  assert.deepEqual(
    teams.map((team) => team.title),
    ['分析师团队', '研究团队', '交易团队', '风险管理', '投资组合管理']
  )
  assert.deepEqual(
    teams[0].agents.map((agent) => agent.agent_name),
    ['市场分析师', '情绪分析师', '新闻分析师', '基本面分析师']
  )
  assert.deepEqual(
    teams[1].agents.map((agent) => agent.agent_name),
    ['看多研究员', '看空研究员', '研究经理']
  )
})

test('buildRunReportTeams prefers agent-level sections and falls back to team-level sections', () => {
  const run = {
    asset_type: 'stock',
    selected_analysts: ['news']
  }
  const reports = [
    { section: 'news_report' },
    { section: 'research_manager_report' },
    { section: 'trader_investment_plan' },
    { section: 'risk_debate' },
    { section: 'final_trade_decision' }
  ]

  const teams = buildRunReportTeams(run, reports)

  assert.equal(teams[1].agents[2].section, 'research_manager_report')
  assert.equal(teams[2].agents[0].section, 'trader_investment_plan')
  assert.equal(teams[3].agents[0].section, 'risk_debate')
  assert.equal(teams[4].agents[0].section, 'final_trade_decision')
  assert.equal(teams[1].agents[0].missing, true)
  assert.equal(teams[3].agents[0].fallback_label, '团队辩论汇总')
})

test('buildRunReportTeams omits downstream teams for macro runs', () => {
  const run = {
    asset_type: 'macro',
    selected_analysts: ['news']
  }

  const teams = buildRunReportTeams(run, [])

  assert.deepEqual(teams.map((team) => team.title), ['分析师团队'])
})

test('buildRunReportTeams uses streaming content before final report exists', () => {
  const run = {
    asset_type: 'stock',
    selected_analysts: ['news']
  }

  const teams = buildRunReportTeams(run, [], {
    news_report: {
      section: 'news_report',
      title: 'News Analysis',
      agent_name: 'News Analyst',
      content_markdown: 'partial news body',
      updated_at: '2026-06-19T09:00:00Z'
    }
  })

  assert.equal(teams[0].agents[0].missing, false)
  assert.equal(teams[0].agents[0].streaming, true)
  assert.equal(teams[0].agents[0].content_markdown, 'partial news body')
})
