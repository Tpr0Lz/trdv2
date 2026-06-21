<template>
  <app-shell title="运行控制台" subtitle="创建并观察一次智能体协作">
    <header class="console-header">
      <div>
        <p class="eyebrow">运行控制台</p>
        <h1>创建并观察一次智能体协作</h1>
      </div>
      <n-button secondary @click="router.push('/runs')">运行历史</n-button>
    </header>
    <run-create-panel
      :defaults="settings.current"
      :loading="runs.loading"
      class="create-panel"
      @create="handleCreate"
    />
  </app-shell>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

import AppShell from '../components/layout/AppShell.vue'
import RunCreatePanel from '../components/runs/RunCreatePanel.vue'
import type { RunCreatePayload } from '../api/runs'
import { useRunsStore } from '../stores/runs'
import { useSettingsStore } from '../stores/settings'

const router = useRouter()
const runs = useRunsStore()
const settings = useSettingsStore()

onMounted(() => {
  settings.fetch()
})

async function handleCreate(payload: RunCreatePayload) {
  const run = await runs.create(payload)
  router.push(`/runs/${run.id}`)
}
</script>

<style scoped>
.console-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.eyebrow {
  margin: 0 0 8px;
  color: #2f66d0;
  font-weight: 700;
}

h1,
h2 {
  margin: 0;
}

.create-panel {
  margin-top: 24px;
}
</style>
