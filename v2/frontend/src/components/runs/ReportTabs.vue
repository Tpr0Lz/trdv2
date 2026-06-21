<template>
  <div class="report-panel">
    <n-empty v-if="teams.length === 0" description="暂无报告产物" />
    <div v-else class="team-layout">
      <n-tabs v-model:value="activeTeamKey" type="line" animated class="team-tabs">
        <n-tab-pane
          v-for="team in teams"
          :key="team.key"
          :name="team.key"
          :tab="team.title"
        >
          <div class="team-panel">
            <aside class="agent-sidebar">
              <button
                v-for="agent in team.agents"
                :key="agent.key"
                type="button"
                class="agent-item"
                :class="{ active: agent.key === activeAgentKey, missing: agent.missing }"
                @click="activeAgentKey = agent.key"
              >
                <strong>{{ agent.agent_name }}</strong>
                <span>{{ agent.missing ? '尚未生成' : agent.title }}</span>
              </button>
            </aside>
            <section class="report-detail">
              <template v-if="activeAgent">
                <div class="report-header">
                  <div>
                    <h3>{{ activeAgent.agent_name }}</h3>
                    <p>{{ activeAgent.title }}</p>
                  </div>
                  <div class="report-meta">
                    <span>{{ activeAgent.section }}</span>
                    <span v-if="activeAgent.updated_at">
                      v{{ activeAgent.version }} · {{ new Date(activeAgent.updated_at).toLocaleString() }}
                    </span>
                    <span v-else>尚未生成</span>
                  </div>
                </div>
                <n-alert v-if="activeAgent.streaming" type="success" class="report-alert">
                  正在流式生成，内容会持续更新。
                </n-alert>
                <n-alert
                  v-else-if="activeAgent.updated_at && !activeAgent.missing"
                  type="info"
                  class="report-alert"
                >
                  报告生成完毕。
                </n-alert>
                <n-alert v-if="activeAgent.fallback_label" type="info" class="report-alert">
                  当前展示的是 {{ activeAgent.fallback_label }}。
                </n-alert>
                <n-alert v-if="activeAgent.missing" type="warning" class="report-alert">
                  该 agent 还没有生成报告。
                </n-alert>
                <report-body-with-citations
                  :content="activeAgent.content_markdown"
                  @select-citation="emit('selectCitation', $event)"
                />
              </template>
            </section>
          </div>
        </n-tab-pane>
      </n-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { Run, RunReport, StreamingReport } from '../../api/runs'
import {
  buildRunReportTeams,
  findInitialReportSelection
} from './reportTabsModel'
import ReportBodyWithCitations from './ReportBodyWithCitations.vue'

const props = defineProps<{
  run: Run | null
  reports: RunReport[]
  streamingReports: Record<string, StreamingReport>
}>()

const emit = defineEmits<{
  selectCitation: [citationKey: string]
}>()

const teams = computed(() => buildRunReportTeams(props.run, props.reports, props.streamingReports))
const activeTeamKey = ref<string | null>(null)
const activeAgentKey = ref<string | null>(null)

const activeTeam = computed(() => teams.value.find((team) => team.key === activeTeamKey.value) ?? null)
const activeAgent = computed(
  () => activeTeam.value?.agents.find((agent) => agent.key === activeAgentKey.value) ?? null
)

watch(
  teams,
  (nextTeams) => {
    const currentTeam = nextTeams.find((team) => team.key === activeTeamKey.value)
    if (!currentTeam) {
      const initialSelection = findInitialReportSelection(nextTeams)
      activeTeamKey.value = initialSelection.teamKey
      activeAgentKey.value = initialSelection.agentSection
      return
    }

    const currentAgent =
      currentTeam.agents.find((agent) => agent.key === activeAgentKey.value) ?? null
    if (currentAgent) {
      return
    }

    // 中文注释：仅当当前选中的 agent 已不存在时，才回退到当前 team 的第一个可见 agent。
    const fallbackAgent = currentTeam.agents.find((agent) => !agent.missing) ?? currentTeam.agents[0] ?? null
    activeAgentKey.value = fallbackAgent?.key ?? null
  },
  { immediate: true }
)

watch(activeTeamKey, (nextKey) => {
  const nextTeam = teams.value.find((team) => team.key === nextKey)
  if (!nextTeam) {
    activeAgentKey.value = null
    return
  }
  const currentAgent = nextTeam.agents.find((agent) => agent.key === activeAgentKey.value)
  if (currentAgent) {
    return
  }
  const fallbackAgent = nextTeam.agents.find((agent) => !agent.missing) ?? nextTeam.agents[0] ?? null
  activeAgentKey.value = fallbackAgent?.key ?? null
})
</script>

<style scoped>
.report-panel {
  min-height: 360px;
}

.team-layout {
  min-height: 320px;
}

.team-panel {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 18px;
  min-height: 320px;
}

.agent-sidebar {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.agent-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  padding: 14px 16px;
  border: 1px solid #dbe4f0;
  border-radius: 10px;
  background: #f8fbff;
  color: #243047;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    background 0.2s ease,
    box-shadow 0.2s ease;
}

.agent-item strong {
  font-size: 14px;
}

.agent-item span {
  color: #667085;
  font-size: 12px;
}

.agent-item.active {
  border-color: #18a058;
  background: #eefaf3;
  box-shadow: 0 8px 24px rgba(24, 160, 88, 0.08);
}

.agent-item.missing {
  border-style: dashed;
}

.report-detail {
  min-width: 0;
}

.report-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.report-header h3 {
  margin: 0;
  color: #243047;
  font-size: 20px;
}

.report-header p {
  margin: 6px 0 0;
  color: #667085;
  font-size: 13px;
}

.report-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  color: #667085;
  font-size: 12px;
}

.report-alert {
  margin-bottom: 12px;
}

@media (max-width: 920px) {
  .team-panel {
    grid-template-columns: 1fr;
  }

  .agent-sidebar {
    overflow-x: auto;
  }

  .report-header {
    flex-direction: column;
  }

  .report-meta {
    align-items: flex-start;
  }
}
</style>
