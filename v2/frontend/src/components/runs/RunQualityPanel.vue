<template>
  <n-card title="质量检查" class="quality-card">
    <n-empty v-if="!quality" description="暂无质量评估" />
    <div v-else>
      <div class="quality-summary">
        <n-progress
          type="circle"
          :percentage="quality.score"
          :status="qualityProgressStatus"
        />
        <div>
          <n-tag :type="qualityTagType">{{ qualityStatusLabel(quality.status) }}</n-tag>
          <p>基于报告完整性、RAG 引用、指标和生命周期的确定性检查。</p>
        </div>
      </div>
      <n-list bordered>
        <n-list-item v-for="check in quality.checks" :key="check.id">
          <div class="check-row">
            <div>
              <strong>{{ check.title }}</strong>
              <p>{{ check.summary }}</p>
            </div>
            <n-tag :type="checkTagType(check.status)">{{ qualityStatusLabel(check.status) }}</n-tag>
          </div>
        </n-list-item>
      </n-list>
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { RunQuality } from '../../api/runs'

const props = defineProps<{
  quality: RunQuality | null
}>()

const qualityTagType = computed(() => checkTagType(props.quality?.status ?? 'info'))

const qualityProgressStatus = computed(() => {
  // 中文注释：Naive UI 的进度状态和后端质量状态名称不同，这里做一次轻量映射。
  if (props.quality?.status === 'fail') return 'error'
  if (props.quality?.status === 'warning') return 'warning'
  return 'success'
})

function checkTagType(status: string) {
  const typeByStatus: Record<string, 'default' | 'error' | 'info' | 'success' | 'warning'> = {
    pass: 'success',
    warning: 'warning',
    fail: 'error',
    info: 'default'
  }
  return typeByStatus[status] ?? 'default'
}

function qualityStatusLabel(status: string) {
  const labelByStatus: Record<string, string> = {
    pass: '通过',
    warning: '警告',
    fail: '失败',
    info: '信息'
  }
  return labelByStatus[status] ?? status
}
</script>

<style scoped>
.quality-card {
  height: 100%;
}

.quality-summary {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 16px;
}

.quality-summary p,
.check-row p {
  margin: 6px 0 0;
  color: #667085;
}

.check-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}
</style>
