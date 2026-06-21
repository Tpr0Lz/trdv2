<template>
  <app-shell title="设置" subtitle="管理默认模型和运行参数">
    <n-card class="settings-card">
      <n-spin :show="settings.loading">
        <n-form v-if="settings.current" :model="form" label-placement="top">
          <div class="form-grid">
            <n-form-item label="LLM 供应商">
              <n-select v-model:value="form.default_llm_provider" :options="providerOptions" filterable />
            </n-form-item>
            <n-form-item label="深度模型">
              <n-select v-model:value="deepModelSelection" :options="deepModelOptions" filterable />
            </n-form-item>
            <n-form-item label="快速模型">
              <n-select v-model:value="quickModelSelection" :options="quickModelOptions" filterable />
            </n-form-item>
            <n-form-item label="输出语言">
              <n-select v-model:value="form.default_output_language" :options="languageOptions" />
            </n-form-item>
          </div>
          <div v-if="showCustomModels" class="form-grid custom-models">
            <n-form-item v-if="deepModelSelection === 'custom'" label="自定义深度模型">
              <n-input v-model:value="customDeepModel" placeholder="输入 TradingAgents 支持的模型 ID" />
            </n-form-item>
            <n-form-item v-if="quickModelSelection === 'custom'" label="自定义快速模型">
              <n-input v-model:value="customQuickModel" placeholder="输入 TradingAgents 支持的模型 ID" />
            </n-form-item>
          </div>
          <div class="form-grid key-grid">
            <n-form-item label="DeepSeek API Key">
              <n-input
                v-model:value="form.deepseek_api_key"
                type="password"
                show-password-on="click"
                placeholder="请输入 DeepSeek API Key"
              />
            </n-form-item>
            <n-form-item label="FRED API Key">
              <n-input
                v-model:value="form.fred_api_key"
                type="password"
                show-password-on="click"
                placeholder="FRED API 密钥"
              />
            </n-form-item>
          </div>
          <div class="settings-row">
            <n-form-item label="研究深度">
              <n-input-number v-model:value="form.default_research_depth" :min="1" :max="5" />
            </n-form-item>
            <n-form-item label="检查点">
              <n-switch v-model:value="form.default_checkpoint_enabled" />
            </n-form-item>
          </div>
          <n-form-item label="默认分析师">
            <n-checkbox-group v-model:value="form.default_analysts">
              <n-space>
                <n-checkbox value="market">市场</n-checkbox>
                <n-checkbox value="social">情绪</n-checkbox>
                <n-checkbox value="news">新闻</n-checkbox>
                <n-checkbox value="fundamentals">基本面</n-checkbox>
              </n-space>
            </n-checkbox-group>
          </n-form-item>
          <n-alert v-if="error" type="error" class="form-alert">{{ error }}</n-alert>
          <n-alert v-if="saved" type="success" class="form-alert">配置已保存</n-alert>
          <n-button type="primary" :loading="settings.saving" @click="handleSave">
            保存设置
          </n-button>
        </n-form>
        <n-empty v-else description="正在加载已保存配置" />
      </n-spin>
    </n-card>
    <n-card class="settings-card rag-card" title="SPY RAG 资料">
      <n-spin :show="rag.loading">
        <n-space vertical :size="14">
          <n-space align="center">
            <n-button type="primary" secondary :loading="rag.importing" @click="handleImportRag">
              导入内置 SPY RAG 资料
            </n-button>
            <label class="rag-upload">
              <input type="file" accept=".md,.txt,.csv" @change="handleUploadRag" />
              <span>{{ rag.uploading ? '上传中...' : '上传 RAG 文件' }}</span>
            </label>
            <n-alert v-if="rag.lastImport" :type="ragImportAlertType" class="rag-import-alert">
              {{ ragImportMessage }}
            </n-alert>
          </n-space>
          <n-empty v-if="rag.sources.length === 0" description="当前还没有导入任何 RAG 资料" />
          <n-data-table v-else :columns="ragColumns" :data="rag.sources" :pagination="false" />
        </n-space>
      </n-spin>
    </n-card>
  </app-shell>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, watch } from 'vue'
import { NButton, NTag } from 'naive-ui'

import AppShell from '../components/layout/AppShell.vue'
import type { AppSettings, AppSettingsUpdatePayload } from '../api/settings'
import type { RagSource } from '../api/rag'
import {
  firstModel,
  isKnownProviderModel,
  optionsForProvider,
  providerOptions
} from '../catalog/llmOptions'
import { useRagStore } from '../stores/rag'
import { useSettingsStore } from '../stores/settings'

const settings = useSettingsStore()
const rag = useRagStore()
const error = ref('')
const saved = ref(false)
const deepModelSelection = ref('deepseek-v4-pro')
const quickModelSelection = ref('deepseek-v4-flash')
const customDeepModel = ref('')
const customQuickModel = ref('')

const form = reactive<AppSettingsUpdatePayload>({
  default_llm_provider: 'deepseek',
  default_deep_model: 'deepseek-v4-pro',
  default_quick_model: 'deepseek-v4-flash',
  default_output_language: 'Chinese',
  default_analysts: ['market', 'social', 'news', 'fundamentals'],
  default_research_depth: 1,
  default_checkpoint_enabled: true,
  deepseek_api_key: '',
  fred_api_key: ''
})

const languageOptions = [
  { label: '英文', value: 'English' },
  { label: '中文', value: 'Chinese' }
]
const ragColumns = [
  { title: '资料标题', key: 'title' },
  { title: '范围', key: 'scope' },
  { title: '类型', key: 'source_type' },
  { title: '来源', key: 'source_name' },
  {
    title: '状态',
    key: 'status',
    render: (row: RagSource) =>
      h(
        NTag,
        { size: 'small', type: row.is_deleted ? 'warning' : 'success' },
        { default: () => (row.is_deleted ? '已停用' : '已启用') }
      )
  },
  {
    title: '发布日期',
    key: 'published_at',
    render: (row: RagSource) => row.published_at ?? '未知'
  },
  {
    title: '操作',
    key: 'action',
    render: (row: RagSource) =>
      h(
        NButton,
        {
          size: 'small',
          secondary: true,
          type: row.is_deleted ? 'primary' : 'warning',
          loading: rag.mutatingSourceId === row.source_id,
          onClick: () => handleToggleRag(row)
        },
        { default: () => (row.is_deleted ? '恢复' : '停用') }
      )
  }
]

const deepModelOptions = computed(() => optionsForProvider(form.default_llm_provider).deep)
const quickModelOptions = computed(() => optionsForProvider(form.default_llm_provider).quick)
const showCustomModels = computed(() => {
  return deepModelSelection.value === 'custom' || quickModelSelection.value === 'custom'
})
const ragImportAlertType = computed(() => {
  if (!rag.lastImport) return 'success'
  return rag.lastImport.documents_imported > 0 || rag.lastImport.chunks_imported > 0
    ? 'success'
    : 'info'
})
const ragImportMessage = computed(() => {
  if (!rag.lastImport) return ''
  if (rag.lastImport.documents_imported === 0 && rag.lastImport.chunks_imported === 0) {
    // 中文注释：内置 RAG 导入是幂等的，0/0 表示资料已存在，不是按钮失效。
    return 'SPY RAG 资料已存在，本次没有导入新文档。'
  }
  return `已导入 ${rag.lastImport.documents_imported} 个文档 / ${rag.lastImport.chunks_imported} 个分块`
})

onMounted(() => {
  settings.fetch()
  rag.fetchSources()
})

watch(
  () => settings.current,
  (current) => {
    if (!current) return
    Object.assign(form, toPayload(current))
    applyModelSelection('deep', current.default_deep_model)
    applyModelSelection('quick', current.default_quick_model)
  },
  { immediate: true }
)

watch(
  () => form.default_llm_provider,
  (provider) => {
    // 中文注释：Settings 里切换供应商时，同步切换到该供应商可用的默认模型。
    if (!isKnownProviderModel(provider, 'deep', deepModelSelection.value)) {
      deepModelSelection.value = firstModel(provider, 'deep')
      customDeepModel.value = ''
    }
    if (!isKnownProviderModel(provider, 'quick', quickModelSelection.value)) {
      quickModelSelection.value = firstModel(provider, 'quick')
      customQuickModel.value = ''
    }
  }
)

async function handleSave() {
  error.value = ''
  saved.value = false
  const deepModel = resolveModel(deepModelSelection.value, customDeepModel.value)
  const quickModel = resolveModel(quickModelSelection.value, customQuickModel.value)
  if (form.default_analysts.length === 0) {
    error.value = '至少选择一位分析师'
    return
  }
  if (!deepModel || !quickModel) {
    error.value = '自定义模型 ID 不能为空'
    return
  }
  try {
    // 中文注释：保存默认配置，不影响已经创建的历史 run 快照。
    await settings.update({
      ...form,
      default_deep_model: deepModel,
      default_quick_model: quickModel,
      default_analysts: [...form.default_analysts]
    })
    saved.value = true
  } catch {
    error.value = '保存失败，请检查后端服务'
  }
}

async function handleImportRag() {
  try {
    await rag.importSpySources()
  } catch {
    error.value = 'RAG 资料导入失败，请检查后端服务'
  }
}

async function handleUploadRag(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    // 中文注释：原始文件只上传给后端解析入库，前端不保存文件内容。
    await rag.uploadSource(file)
  } catch {
    error.value = 'RAG 文件上传失败，请确认文件是 UTF-8 的 .md/.txt/.csv'
  } finally {
    input.value = ''
  }
}

async function handleToggleRag(source: RagSource) {
  const confirmed = source.is_deleted
    ? window.confirm(`确认恢复 RAG 资料“${source.source_id}”吗？恢复后新的 run 可以再次检索到它。`)
    : window.confirm(`确认停用 RAG 资料“${source.source_id}”吗？历史证据会继续保留。`)
  if (!confirmed) return
  try {
    // 中文注释：这里只切换资料启用状态，不改历史 evidence。
    if (source.is_deleted) {
      await rag.restoreSource(source.source_id)
    } else {
      await rag.deleteSource(source.source_id)
    }
  } catch {
    error.value = source.is_deleted ? 'RAG 资料恢复失败，请检查后端服务' : 'RAG 资料停用失败，请检查后端服务'
  }
}

function toPayload(current: AppSettings): AppSettingsUpdatePayload {
  return {
    default_llm_provider: current.default_llm_provider,
    default_deep_model: current.default_deep_model,
    default_quick_model: current.default_quick_model,
    default_output_language: current.default_output_language,
    default_analysts: [...current.default_analysts],
    default_research_depth: current.default_research_depth,
    default_checkpoint_enabled: current.default_checkpoint_enabled,
    deepseek_api_key: current.deepseek_api_key,
    fred_api_key: current.fred_api_key
  }
}

function applyModelSelection(mode: 'deep' | 'quick', model: string) {
  const targetSelection = mode === 'deep' ? deepModelSelection : quickModelSelection
  const targetCustom = mode === 'deep' ? customDeepModel : customQuickModel
  if (isKnownProviderModel(form.default_llm_provider, mode, model)) {
    targetSelection.value = model
    targetCustom.value = ''
    return
  }
  targetSelection.value = 'custom'
  targetCustom.value = model
}

function resolveModel(selection: string, customModel: string) {
  return selection === 'custom' ? customModel.trim() : selection
}
</script>

<style scoped>
.settings-card {
  max-width: 1120px;
}

.rag-card {
  margin-top: 18px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.settings-row {
  display: grid;
  grid-template-columns: 180px 180px;
  gap: 14px;
}

.custom-models {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.key-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.form-alert {
  margin-bottom: 16px;
}

.rag-import-alert {
  padding: 7px 12px;
}

.rag-upload {
  position: relative;
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border: 1px solid #18a058;
  border-radius: 4px;
  color: #18a058;
  cursor: pointer;
}

.rag-upload input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

@media (max-width: 920px) {
  .form-grid,
  .settings-row,
  .custom-models,
  .key-grid {
    grid-template-columns: 1fr;
  }
}
</style>
