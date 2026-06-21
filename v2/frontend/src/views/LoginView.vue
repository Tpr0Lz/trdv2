<template>
  <main class="login-view">
    <section class="login-panel">
      <p class="eyebrow">TradingAgents V2</p>
      <h1>智能体运行观测台</h1>
      <p class="summary">登录后创建、观察和复盘 TradingAgents 多智能体分析任务。</p>
      <n-form :model="form" size="large" @submit.prevent="handleSubmit">
        <n-form-item label="用户名">
          <n-input v-model:value="form.username" autocomplete="username" placeholder="请输入用户名" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input
            v-model:value="form.password"
            type="password"
            autocomplete="current-password"
            show-password-on="click"
            placeholder="请输入密码"
          />
        </n-form-item>
        <n-alert v-if="error" type="error" class="error-alert">{{ error }}</n-alert>
        <n-button type="primary" size="large" block :loading="auth.loading" @click="handleSubmit">
          登录
        </n-button>
      </n-form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const error = ref('')
const form = reactive({
  username: 'admin',
  password: ''
})

async function handleSubmit() {
  error.value = ''
  try {
    await auth.login(form.username, form.password)
    router.push('/')
  } catch {
    error.value = '用户名或密码不正确'
  }
}
</script>

<style scoped>
.login-view {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px;
}

.login-panel {
  width: min(440px, 100%);
  padding: 32px;
  border: 1px solid #d9e1ee;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 18px 45px rgb(31 45 61 / 8%);
}

.eyebrow {
  margin: 0 0 10px;
  color: #2f66d0;
  font-weight: 700;
}

h1 {
  margin: 0;
  font-size: 28px;
}

.summary {
  margin: 14px 0 24px;
  color: #5b677a;
  line-height: 1.7;
}

.error-alert {
  margin-bottom: 16px;
}
</style>
