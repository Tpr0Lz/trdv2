import { defineStore } from 'pinia'

import * as settingsApi from '../api/settings'
import type { AppSettings, AppSettingsUpdatePayload } from '../api/settings'

interface SettingsState {
  current: AppSettings | null
  loading: boolean
  saving: boolean
}

export const useSettingsStore = defineStore('settings', {
  state: (): SettingsState => ({
    current: null,
    loading: false,
    saving: false
  }),
  actions: {
    async fetch() {
      this.loading = true
      try {
        this.current = await settingsApi.getSettings()
      } finally {
        this.loading = false
      }
    },
    async update(payload: AppSettingsUpdatePayload) {
      this.saving = true
      try {
        this.current = await settingsApi.updateSettings(payload)
      } finally {
        this.saving = false
      }
    }
  }
})
