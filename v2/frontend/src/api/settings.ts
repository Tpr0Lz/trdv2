import { http } from './http'

export interface AppSettings {
  id: string
  user_id: string
  default_llm_provider: string
  default_deep_model: string
  default_quick_model: string
  default_output_language: string
  default_analysts: string[]
  default_research_depth: number
  default_checkpoint_enabled: boolean
  deepseek_api_key: string
  fred_api_key: string
  created_at: string
  updated_at: string
}

export type AppSettingsUpdatePayload = Omit<AppSettings, 'id' | 'user_id' | 'created_at' | 'updated_at'>

export async function getSettings(): Promise<AppSettings> {
  const response = await http.get<AppSettings>('/settings')
  return response.data
}

export async function updateSettings(payload: AppSettingsUpdatePayload): Promise<AppSettings> {
  const response = await http.put<AppSettings>('/settings', payload)
  return response.data
}
