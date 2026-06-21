import { http } from './http'

export interface RagSource {
  id: string
  source_id: string
  ticker: string
  scope: string
  source_type: string
  source_name: string
  title: string
  published_at: string | null
  retrieved_at: string | null
  confidence: string
  license_note: string
  is_deleted: boolean
  deleted_at: string | null
  created_at: string
  updated_at: string
}

export interface RagImportResult {
  documents_imported: number
  chunks_imported: number
}

export async function listRagSources(): Promise<RagSource[]> {
  const response = await http.get<{ items: RagSource[] }>('/rag/sources')
  return response.data.items
}

export async function importSpySources(): Promise<RagImportResult> {
  const response = await http.post<RagImportResult>('/rag/import-spy-sources')
  return response.data
}

export async function uploadRagSource(file: File): Promise<RagImportResult> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await http.post<RagImportResult>('/rag/upload-source', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return response.data
}

export async function deleteRagSource(sourceId: string): Promise<void> {
  await http.delete(`/rag/sources/${encodeURIComponent(sourceId)}`)
}

export async function restoreRagSource(sourceId: string): Promise<void> {
  await http.post(`/rag/sources/${encodeURIComponent(sourceId)}/restore`)
}
