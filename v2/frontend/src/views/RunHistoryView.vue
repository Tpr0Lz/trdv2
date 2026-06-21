<template>
  <app-shell title="运行历史" subtitle="查看历史智能体运行记录">
    <n-card>
      <n-spin :show="runs.loading">
        <n-empty v-if="runs.items.length === 0" description="暂无任务" />
        <n-table v-else :bordered="false">
          <thead>
            <tr>
              <th>标的</th>
              <th>分析日期</th>
              <th>状态</th>
              <th>创建时间</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="run in runs.items" :key="run.id">
              <td>{{ run.ticker }}</td>
              <td>{{ run.analysis_date }}</td>
              <td><run-status-tag :status="run.status" /></td>
              <td>{{ new Date(run.created_at).toLocaleString() }}</td>
              <td><n-button text type="primary" @click="router.push(`/runs/${run.id}`)">查看</n-button></td>
            </tr>
          </tbody>
        </n-table>
      </n-spin>
    </n-card>
  </app-shell>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

import AppShell from '../components/layout/AppShell.vue'
import RunStatusTag from '../components/runs/RunStatusTag.vue'
import { useRunsStore } from '../stores/runs'

const router = useRouter()
const runs = useRunsStore()

onMounted(() => {
  runs.fetchList()
})
</script>
