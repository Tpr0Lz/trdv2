import type { Run, RunReport, StreamingReport } from '../../api/runs'

export interface DisplayReportAgent {
  key: string
  section: string
  title: string
  team: string
  agent_name: string
  content_markdown: string
  version: number | null
  updated_at: string | null
  missing: boolean
  fallback_label: string | null
  streaming: boolean
}

export interface DisplayReportTeam {
  key: string
  title: string
  agents: DisplayReportAgent[]
}

const MISSING_CONTENT = '该阶段暂无输出，通常表示任务在到达这里之前就失败或中断了。'

const ANALYST_AGENT_DEFS: Record<string, { section: string; title: string; agentName: string }> = {
  market: { section: 'market_report', title: '市场分析', agentName: '市场分析师' },
  social: {
    section: 'sentiment_report',
    title: '情绪分析',
    agentName: '情绪分析师'
  },
  news: { section: 'news_report', title: '新闻分析', agentName: '新闻分析师' },
  fundamentals: {
    section: 'fundamentals_report',
    title: '基本面分析',
    agentName: '基本面分析师'
  }
}

interface AgentDefinition {
  primarySection: string
  title: string
  agentName: string
  fallbackSections?: string[]
  fallbackLabel?: string
}

export function buildRunReportTeams(
  run: Run | null,
  reports: RunReport[],
  streamingReports: Record<string, StreamingReport> = {}
): DisplayReportTeam[] {
  if (!run) return []

  const reportMap = new Map(reports.map((report) => [report.section, report]))
  const streamingMap = new Map(Object.entries(streamingReports))
  const teams: DisplayReportTeam[] = []
  const analystTeam = buildAnalystTeam(run, reportMap, streamingMap)
  if (analystTeam.agents.length > 0) {
    teams.push(analystTeam)
  }

  if (run.asset_type !== 'macro') {
    teams.push(
      buildTeam('research_team', '研究团队', reportMap, streamingMap, [
        {
          primarySection: 'bull_researcher_report',
          title: '看多研究',
          agentName: '看多研究员'
        },
        {
          primarySection: 'bear_researcher_report',
          title: '看空研究',
          agentName: '看空研究员'
        },
        {
          primarySection: 'research_manager_report',
          title: '研究管理',
          agentName: '研究经理',
          fallbackSections: ['investment_plan'],
          fallbackLabel: '研究团队结论'
        }
      ]),
      buildTeam('trading_team', '交易团队', reportMap, streamingMap, [
        {
          primarySection: 'trader_report',
          title: '交易执行',
          agentName: '交易员',
          fallbackSections: ['trader_investment_plan'],
          fallbackLabel: '交易计划'
        }
      ]),
      buildTeam('risk_management', '风险管理', reportMap, streamingMap, [
        {
          primarySection: 'aggressive_analyst_report',
          title: '激进视角',
          agentName: '激进分析师',
          fallbackSections: ['risk_debate'],
          fallbackLabel: '团队辩论汇总'
        },
        {
          primarySection: 'neutral_analyst_report',
          title: '中性视角',
          agentName: '中性分析师',
          fallbackSections: ['risk_debate'],
          fallbackLabel: '团队辩论汇总'
        },
        {
          primarySection: 'conservative_analyst_report',
          title: '保守视角',
          agentName: '保守分析师',
          fallbackSections: ['risk_debate'],
          fallbackLabel: '团队辩论汇总'
        }
      ]),
      buildTeam('portfolio_management', '投资组合管理', reportMap, streamingMap, [
        {
          primarySection: 'portfolio_manager_report',
          title: '组合决策',
          agentName: '投资组合经理',
          fallbackSections: ['final_trade_decision'],
          fallbackLabel: '最终交易决策'
        }
      ])
    )
  }

  return teams
}

export function findInitialReportSelection(teams: DisplayReportTeam[]): {
  teamKey: string | null
  agentSection: string | null
} {
  for (const team of teams) {
    const firstReadyAgent = team.agents.find((agent) => !agent.missing) ?? team.agents[0]
    if (firstReadyAgent) {
      return {
        teamKey: team.key,
        agentSection: firstReadyAgent.section
      }
    }
  }
  return {
    teamKey: null,
    agentSection: null
  }
}

function buildAnalystTeam(
  run: Run,
  reportMap: Map<string, RunReport>,
  streamingMap: Map<string, StreamingReport>
): DisplayReportTeam {
  return {
    key: 'analyst_team',
    title: '分析师团队',
    agents: run.selected_analysts
      .map((analyst) => ANALYST_AGENT_DEFS[analyst])
      .filter((definition): definition is NonNullable<typeof definition> => Boolean(definition))
      .map((definition) =>
        buildAgent('分析师团队', reportMap, streamingMap, {
          primarySection: definition.section,
          title: definition.title,
          agentName: definition.agentName
        })
      )
  }
}

function buildTeam(
  key: string,
  title: string,
  reportMap: Map<string, RunReport>,
  streamingMap: Map<string, StreamingReport>,
  definitions: AgentDefinition[]
): DisplayReportTeam {
  return {
    key,
    title,
    agents: definitions.map((definition) => buildAgent(title, reportMap, streamingMap, definition))
  }
}

function buildAgent(
  team: string,
  reportMap: Map<string, RunReport>,
  streamingMap: Map<string, StreamingReport>,
  definition: AgentDefinition
): DisplayReportAgent {
  const matchedReport = findReport(reportMap, definition.primarySection, definition.fallbackSections)
  if (matchedReport) {
    return {
      key: definition.primarySection,
      section: matchedReport.section,
      title: definition.title,
      team,
      agent_name: definition.agentName,
      content_markdown: matchedReport.content_markdown,
      version: matchedReport.version,
      updated_at: matchedReport.updated_at,
      missing: false,
      fallback_label:
        matchedReport.section === definition.primarySection ? null : (definition.fallbackLabel ?? null),
      streaming: false
    }
  }

  const streamingReport = streamingMap.get(definition.primarySection)
  if (streamingReport && streamingReport.content_markdown.trim()) {
    return {
      key: definition.primarySection,
      section: definition.primarySection,
      title: definition.title,
      team,
      agent_name: definition.agentName,
      content_markdown: streamingReport.content_markdown,
      version: null,
      updated_at: streamingReport.updated_at,
      missing: false,
      fallback_label: null,
      streaming: true
    }
  }

  return {
    key: definition.primarySection,
    section: definition.primarySection,
    title: definition.title,
    team,
    agent_name: definition.agentName,
    content_markdown: MISSING_CONTENT,
    version: null,
    updated_at: null,
    missing: true,
    fallback_label: null,
    streaming: false
  }
}

function findReport(
  reportMap: Map<string, RunReport>,
  primarySection: string,
  fallbackSections: string[] = []
) {
  const primaryReport = reportMap.get(primarySection)
  if (primaryReport) {
    return primaryReport
  }
  for (const section of fallbackSections) {
    const fallbackReport = reportMap.get(section)
    if (fallbackReport) {
      return fallbackReport
    }
  }
  return null
}
