import { defineStore } from 'pinia'

import * as authApi from '../api/auth'
import type { User } from '../api/auth'

interface AuthState {
  user: User | null
  initialized: boolean
  loading: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: null,
    initialized: false,
    loading: false
  }),
  getters: {
    isAuthenticated: (state) => state.user !== null
  },
  actions: {
    async initialize() {
      if (this.initialized) return
      try {
        this.user = await authApi.fetchCurrentUser()
      } catch {
        this.user = null
      } finally {
        this.initialized = true
      }
    },
    async login(username: string, password: string) {
      this.loading = true
      try {
        this.user = await authApi.login({ username, password })
        this.initialized = true
      } finally {
        this.loading = false
      }
    },
    async logout() {
      await authApi.logout()
      this.user = null
      this.initialized = true
    }
  }
})
