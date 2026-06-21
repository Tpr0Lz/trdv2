<template>
  <div class="report-body">
    <template v-for="(part, index) in parts" :key="index">
      <button
        v-if="part.citationKey"
        type="button"
        class="citation-chip"
        @click="emit('selectCitation', part.citationKey)"
      >
        {{ part.text }}
      </button>
      <span v-else>{{ part.text }}</span>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import { splitReportCitations } from './reportCitations'

const props = defineProps<{
  content: string
}>()

const emit = defineEmits<{
  selectCitation: [citationKey: string]
}>()

const parts = computed(() => splitReportCitations(props.content))
</script>

<style scoped>
.report-body {
  min-height: 240px;
  margin: 0;
  padding: 16px;
  overflow-x: auto;
  border: 1px solid #dde5f2;
  border-radius: 8px;
  background: #fbfcfe;
  color: #243047;
  font-family:
    "Cascadia Code",
    Consolas,
    monospace;
  line-height: 1.7;
  white-space: pre-wrap;
}

.citation-chip {
  margin: 0 2px;
  padding: 1px 6px;
  border: 1px solid #18a058;
  border-radius: 6px;
  background: #eefaf3;
  color: #0f7a43;
  cursor: pointer;
  font: inherit;
}

.citation-chip:hover {
  background: #dff5e9;
}
</style>
