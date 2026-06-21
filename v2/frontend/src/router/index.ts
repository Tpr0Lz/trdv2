import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'run-console',
      component: () => import('../views/RunConsoleView.vue')
    },
    {
      path: '/runs',
      name: 'run-history',
      component: () => import('../views/RunHistoryView.vue')
    },
    {
      path: '/runs/:runId',
      name: 'run-detail',
      component: () => import('../views/RunDetailView.vue')
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsView.vue')
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue')
    }
  ]
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.initialize()
  if (to.name !== 'login' && !auth.isAuthenticated) {
    return { name: 'login' }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'run-console' }
  }
})

export default router
