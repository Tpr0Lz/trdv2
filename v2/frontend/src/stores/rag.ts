import { defineStore } from 'pinia'

import * as ragApi from '../api/rag'
import type { RagImportResult, RagSource } from '../api/rag'

interface RagState {
  sources: RagSource[]
  lastImport: RagImportResult | null
  loading: boolean
  importing: boolean
  uploading: boolean
  mutatingSourceId: string
}

export const useRagStore = defineStore('rag', {
  state: (): RagState => ({
    sources: [],
    lastImport: null,
    loading: false,
    importing: false,
    uploading: false,
    mutatingSourceId: ''
  }),
  actions: {
    async fetchSources() {
      this.loading = true
      try {
        this.sources = await ragApi.listRagSources()
      } finally {
        this.loading = false
      }
    },
    async importSpySources() {
      this.importing = true
      try {
        this.lastImport = await ragApi.importSpySources()
        // 中文注释：导入后立即刷新列表，让 Settings 页面展示当前 RAG 库状态。
        this.sources = await ragApi.listRagSources()
      } finally {
        this.importing = false
      }
    },
    async uploadSource(file: File) {
      this.uploading = true
      try {
        this.lastImport = await ragApi.uploadRagSource(file)
        // 中文注释：上传成功后刷新列表，确认文档已进入 PostgreSQL。
        this.sources = await ragApi.listRagSources()
      } finally {
        this.uploading = false
      }
    },
    async deleteSource(sourceId: string) {
      this.mutatingSourceId = sourceId
      try {
        await ragApi.deleteRagSource(sourceId)
        // 中文注释：停用后刷新列表，已停用资料保留在表格中，便于后续恢复。
        this.sources = await ragApi.listRagSources()
      } finally {
        this.mutatingSourceId = ''
      }
    },
    async restoreSource(sourceId: string) {
      this.mutatingSourceId = sourceId
      try {
        await ragApi.restoreRagSource(sourceId)
        // 中文注释：恢复后刷新列表，让资料重新回到可检索状态。
        this.sources = await ragApi.listRagSources()
      } finally {
        this.mutatingSourceId = ''
      }
    }
  }
})
