<template>
  <div class="evidence-panel">
    <n-empty v-if="items.length === 0" description="暂无证据" />
    <n-space v-else vertical :size="10">
      <div
        v-for="item in items"
        :key="item.id"
        class="evidence-item"
        :class="{ active: item.citation_key === activeCitationKey }"
        :data-citation-key="item.citation_key"
      >
        <div class="evidence-header">
          <strong>{{ item.source_title }}</strong>
          <n-space align="center" :size="8">
            <n-tag v-if="item.citation_key" size="small" type="success">
              {{ item.citation_key }}
            </n-tag>
            <n-tag size="small">{{ item.agent_name }}</n-tag>
          </n-space>
        </div>
        <div class="meta">
          {{ item.source_name }} · {{ item.source_type }}
          <span v-if="item.published_at"> · {{ item.published_at }}</span>
        </div>
        <p>{{ item.excerpt }}</p>
        <n-a v-if="item.url" :href="item.url" target="_blank">查看来源</n-a>
      </div>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import type { RunEvidence } from '../../api/runs'

defineProps<{
  items: RunEvidence[]
  activeCitationKey: string | null
}>()
</script>

<style scoped>
.evidence-item {
  border: 1px solid rgba(120, 120, 120, 0.22);
  border-radius: 10px;
  padding: 12px;
}

.evidence-item.active {
  border-color: #18a058;
  background: #eefaf3;
  box-shadow: 0 8px 24px rgba(24, 160, 88, 0.12);
}

.evidence-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.meta {
  margin-top: 4px;
  color: var(--muted-text-color, #6b7280);
  font-size: 12px;
}

p {
  margin: 8px 0;
}
</style>
