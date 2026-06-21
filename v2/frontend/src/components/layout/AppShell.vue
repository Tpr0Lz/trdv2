<template>
  <n-layout has-sider class="app-shell">
    <n-layout-sider bordered width="236" class="sidebar">
      <div class="brand">
        <span class="brand-mark">TA</span>
        <div>
          <strong>TradingAgents</strong>
          <small>运行观测台</small>
        </div>
      </div>
      <n-menu :value="activeKey" :options="menuOptions" @update:value="go" />
    </n-layout-sider>
    <n-layout>
      <n-layout-header bordered class="topbar">
        <div>
          <strong>{{ title }}</strong>
          <span>{{ subtitle }}</span>
        </div>
        <n-button secondary @click="handleLogout">退出登录</n-button>
      </n-layout-header>
      <n-layout-content class="content">
        <slot />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import type { MenuOption } from 'naive-ui'

import { useAuthStore } from '../../stores/auth'

defineProps<{
  title: string
  subtitle: string
}>()

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const activeKey = computed(() => String(route.name ?? 'run-console'))

const menuOptions: MenuOption[] = [
  {
    key: 'run-console',
    label: () => h(RouterLink, { to: '/' }, { default: () => '运行控制台' })
  },
  {
    key: 'run-history',
    label: () => h(RouterLink, { to: '/runs' }, { default: () => '运行历史' })
  },
  {
    key: 'settings',
    label: () => h(RouterLink, { to: '/settings' }, { default: () => '设置' })
  }
]

function go(key: string) {
  if (key === 'run-console') router.push('/')
  if (key === 'run-history') router.push('/runs')
  if (key === 'settings') router.push('/settings')
}

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.sidebar {
  background: #fbfcfe;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 22px 18px;
}

.brand-mark {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 8px;
  background: #172033;
  color: #ffffff;
  font-weight: 800;
}

.brand small {
  display: block;
  margin-top: 2px;
  color: #6d7788;
}

.topbar {
  display: flex;
  height: 68px;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #ffffff;
}

.topbar span {
  display: block;
  margin-top: 3px;
  color: #6d7788;
}

.content {
  min-height: calc(100vh - 68px);
  padding: 28px;
  background: #f4f7fb;
}
</style>
