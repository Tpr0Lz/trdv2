<template>
  <n-card title="创建分析任务" class="run-create-panel">
    <n-form :model="form" label-placement="top">
      <div class="form-grid">
        <n-form-item label="标的代码">
          <n-input v-model:value="form.ticker" placeholder="NVDA" />
        </n-form-item>
        <n-form-item label="分析日期">
          <n-date-picker v-model:formatted-value="form.analysis_date" type="date" value-format="yyyy-MM-dd" />
        </n-form-item>
        <n-form-item label="资产类型">
          <n-select v-model:value="form.asset_type" :options="assetTypeOptions" />
        </n-form-item>
        <n-form-item label="研究深度">
          <n-input-number v-model:value="form.research_depth" :min="1" :max="5" />
        </n-form-item>
      </div>
      <div class="form-grid wide">
        <n-form-item label="LLM 供应商">
          <n-select v-model:value="form.llm_provider" :options="providerOptions" filterable />
        </n-form-item>
        <n-form-item label="深度模型">
          <n-select v-model:value="deepModelSelection" :options="deepModelOptions" filterable />
        </n-form-item>
        <n-form-item label="快速模型">
          <n-select v-model:value="quickModelSelection" :options="quickModelOptions" filterable />
        </n-form-item>
        <n-form-item label="输出语言">
          <n-select v-model:value="form.output_language" :options="languageOptions" />
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
      <n-form-item label="参与分析师">
        <n-checkbox-group v-model:value="form.selected_analysts">
          <n-space>
            <n-checkbox value="market" :disabled="isMacroMode">市场</n-checkbox>
            <n-checkbox value="social" :disabled="isMacroMode">情绪</n-checkbox>
            <n-checkbox value="news">新闻</n-checkbox>
            <n-checkbox value="fundamentals" :disabled="isMacroMode">基本面</n-checkbox>
          </n-space>
        </n-checkbox-group>
      </n-form-item>
      <n-alert v-if="error" type="error" class="error-alert">{{ error }}</n-alert>
      <n-button type="primary" :loading="loading" @click="submit">创建任务</n-button>
    </n-form>
  </n-card>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import type { RunCreatePayload } from '../../api/runs'
import type { AppSettings } from '../../api/settings'
import {
  firstModel,
  isKnownProviderModel,
  optionsForProvider,
  providerOptions
} from '../../catalog/llmOptions'

const props = defineProps<{
  loading: boolean
  defaults?: AppSettings | null
}>()

const emit = defineEmits<{
  create: [payload: RunCreatePayload]
}>()

const today = new Date().toISOString().slice(0, 10)
const error = ref('')
const deepModelSelection = ref('deepseek-v4-pro')
const quickModelSelection = ref('deepseek-v4-flash')
const customDeepModel = ref('')
const customQuickModel = ref('')
const form = reactive<RunCreatePayload>({
  ticker: 'SPY',
  analysis_date: today,
  asset_type: 'stock',
  selected_analysts: ['market', 'social', 'news', 'fundamentals'],
  research_depth: 1,
  llm_provider: 'deepseek',
  deep_think_llm: 'deepseek-v4-pro',
  quick_think_llm: 'deepseek-v4-flash',
  output_language: 'Chinese'
})

const assetTypeOptions = [
  { label: '宏观（FRED）', value: 'macro' },
  { label: '股票', value: 'stock' },
  { label: '加密货币', value: 'crypto' }
]

const languageOptions = [
  { label: '英文', value: 'English' },
  { label: '中文', value: 'Chinese' }
]

const deepModelOptions = computed(() => optionsForProvider(form.llm_provider).deep)
const quickModelOptions = computed(() => optionsForProvider(form.llm_provider).quick)
const isMacroMode = computed(() => form.asset_type === 'macro')
const showCustomModels = computed(() => {
  return deepModelSelection.value === 'custom' || quickModelSelection.value === 'custom'
})

watch(
  () => props.defaults,
  (defaults) => {
    if (!defaults) return
    // 中文注释：设置页保存的是默认值，本次创建仍可在表单里临时覆盖。
    form.selected_analysts = [...defaults.default_analysts]
    form.research_depth = defaults.default_research_depth
    form.llm_provider = defaults.default_llm_provider
    applyModelSelection('deep', defaults.default_deep_model)
    applyModelSelection('quick', defaults.default_quick_model)
    form.output_language = defaults.default_output_language
    applyAssetTypeDefaults()
  },
  { immediate: true }
)

watch(
  () => form.asset_type,
  () => {
    applyAssetTypeDefaults()
  }
)

watch(
  () => form.llm_provider,
  (provider) => {
    // 中文注释：切换 provider 后收敛到该 provider 的模型目录，避免提交不匹配组合。
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

function submit() {
  error.value = ''
  const deepModel = resolveModel(deepModelSelection.value, customDeepModel.value)
  const quickModel = resolveModel(quickModelSelection.value, customQuickModel.value)
  if (!form.ticker.trim()) {
    error.value = '标的代码不能为空'
    return
  }
  if (form.selected_analysts.length === 0) {
    error.value = '至少选择一位分析师'
    return
  }
  if (!deepModel || !quickModel) {
    error.value = '自定义模型 ID 不能为空'
    return
  }
  // 中文注释：提交时复制表单，避免父组件持有响应式对象引用。
  emit('create', {
    ...form,
    ticker: form.ticker.trim().toUpperCase(),
    selected_analysts: normalizedSelectedAnalysts(),
    deep_think_llm: deepModel,
    quick_think_llm: quickModel
  })
}

function applyAssetTypeDefaults() {
  if (form.asset_type !== 'macro') return
  // 中文注释：FRED 宏观模式只保留 News，避免调用股票行情和基本面工具。
  form.selected_analysts = ['news']
}

function normalizedSelectedAnalysts() {
  return form.asset_type === 'macro' ? ['news'] : [...form.selected_analysts]
}

function applyModelSelection(mode: 'deep' | 'quick', model: string) {
  const targetSelection = mode === 'deep' ? deepModelSelection : quickModelSelection
  const targetCustom = mode === 'deep' ? customDeepModel : customQuickModel
  if (isKnownProviderModel(form.llm_provider, mode, model)) {
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
.run-create-panel {
  max-width: 1120px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.form-grid.wide {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.custom-models {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.error-alert {
  margin-bottom: 16px;
}

@media (max-width: 920px) {
  .form-grid,
  .form-grid.wide,
  .custom-models {
    grid-template-columns: 1fr;
  }
}
</style>
