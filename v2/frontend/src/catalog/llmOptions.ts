export interface SelectOption {
  label: string
  value: string
}

export interface ProviderModelOptions {
  quick: SelectOption[]
  deep: SelectOption[]
}

export const providerOptions: SelectOption[] = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'Google', value: 'google' },
  { label: 'Anthropic', value: 'anthropic' },
  { label: 'xAI', value: 'xai' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: 'Qwen', value: 'qwen' },
  { label: 'GLM', value: 'glm' },
  { label: 'MiniMax', value: 'minimax' },
  { label: 'OpenRouter', value: 'openrouter' },
  { label: 'Mistral', value: 'mistral' },
  { label: 'Kimi (Moonshot)', value: 'kimi' },
  { label: 'Groq', value: 'groq' },
  { label: 'NVIDIA NIM', value: 'nvidia' },
  { label: 'Azure OpenAI', value: 'azure' },
  { label: 'Amazon Bedrock', value: 'bedrock' },
  { label: 'Ollama', value: 'ollama' },
  { label: 'OpenAI-compatible', value: 'openai_compatible' }
]

const customOnly: ProviderModelOptions = {
  quick: [{ label: 'Custom model ID', value: 'custom' }],
  deep: [{ label: 'Custom model ID', value: 'custom' }]
}

const qwenModels: ProviderModelOptions = {
  quick: [
    { label: 'Qwen 3.6 Flash - Latest fast, agentic coding + vision-language', value: 'qwen3.6-flash' },
    { label: 'Qwen 3.5 Flash - Previous-gen fast', value: 'qwen3.5-flash' },
    { label: 'Custom model ID', value: 'custom' }
  ],
  deep: [
    { label: 'Qwen 3.7 Max - Latest flagship reasoning agent, 1M ctx', value: 'qwen3.7-max' },
    { label: 'Qwen 3.6 Plus - Vision-language, agentic coding', value: 'qwen3.6-plus' },
    { label: 'Qwen 3.5 Plus - Previous-gen flagship', value: 'qwen3.5-plus' },
    { label: 'Custom model ID', value: 'custom' }
  ]
}

const glmModels: ProviderModelOptions = {
  quick: [
    { label: 'GLM-5-Turbo - Fast, switchable thinking modes', value: 'glm-5-turbo' },
    { label: 'GLM-4.7 - Previous-gen flagship', value: 'glm-4.7' },
    { label: 'GLM-4.5-Air - Lightweight, cost-efficient', value: 'glm-4.5-air' },
    { label: 'Custom model ID', value: 'custom' }
  ],
  deep: [
    { label: 'GLM-5.1 - Latest flagship, 204K ctx', value: 'glm-5.1' },
    { label: 'GLM-5 - Flagship, 204K ctx', value: 'glm-5' },
    { label: 'GLM-4.7 - Previous-gen flagship', value: 'glm-4.7' },
    { label: 'Custom model ID', value: 'custom' }
  ]
}

const minimaxModels: ProviderModelOptions = {
  quick: [
    { label: 'MiniMax-M2.7-highspeed - Faster M2.7, 204K ctx', value: 'MiniMax-M2.7-highspeed' },
    { label: 'MiniMax-M2.5-highspeed - Previous-gen highspeed, 204K ctx', value: 'MiniMax-M2.5-highspeed' },
    { label: 'MiniMax-M2.1-highspeed - M2.1 highspeed, 204K ctx', value: 'MiniMax-M2.1-highspeed' },
    { label: 'Custom model ID', value: 'custom' }
  ],
  deep: [
    { label: 'MiniMax-M2.7 - Flagship, SOTA on coding/agent benchmarks, 204K ctx', value: 'MiniMax-M2.7' },
    { label: 'MiniMax-M2.7-highspeed - Same quality as M2.7, ~100 TPS', value: 'MiniMax-M2.7-highspeed' },
    { label: 'MiniMax-M2.5 - Previous-gen flagship, 204K ctx', value: 'MiniMax-M2.5' },
    { label: 'MiniMax-M2.1 - Earlier M2 line, 204K ctx', value: 'MiniMax-M2.1' },
    { label: 'MiniMax-M2 - Base M2, 204K ctx', value: 'MiniMax-M2' },
    { label: 'Custom model ID', value: 'custom' }
  ]
}

// 中文注释：选项来自 TradingAgents 的 model_catalog.py 与 cli/utils.py，前端两处表单共用。
export const modelOptionsByProvider: Record<string, ProviderModelOptions> = {
  openai: {
    quick: [
      { label: 'GPT-5.4 Mini - Fast, strong coding and tool use', value: 'gpt-5.4-mini' },
      { label: 'GPT-5.4 Nano - Cheapest, high-volume tasks', value: 'gpt-5.4-nano' },
      { label: 'GPT-5.5 - Latest frontier, 1M context', value: 'gpt-5.5' },
      { label: 'GPT-4.1 - Smartest non-reasoning model', value: 'gpt-4.1' }
    ],
    deep: [
      { label: 'GPT-5.5 - Latest frontier, 1M context', value: 'gpt-5.5' },
      { label: 'GPT-5.4 - Previous-gen frontier, 1M context, cost-effective', value: 'gpt-5.4' },
      { label: 'GPT-5.2 - Strong reasoning, cost-effective', value: 'gpt-5.2' },
      { label: 'GPT-5.5 Pro - Most capable, expensive', value: 'gpt-5.5-pro' }
    ]
  },
  anthropic: {
    quick: [
      { label: 'Claude Sonnet 4.6 - Best speed and intelligence balance', value: 'claude-sonnet-4-6' },
      { label: 'Claude Haiku 4.5 - Fastest with near-frontier intelligence', value: 'claude-haiku-4-5' },
      { label: 'Claude Sonnet 4.5 - High-performance for agents and coding', value: 'claude-sonnet-4-5' }
    ],
    deep: [
      { label: 'Claude Opus 4.8 - Latest frontier, agentic coding and reasoning', value: 'claude-opus-4-8' },
      { label: 'Claude Opus 4.7 - Previous frontier, long-running agents', value: 'claude-opus-4-7' },
      { label: 'Claude Opus 4.6 - Frontier intelligence, agents and coding', value: 'claude-opus-4-6' },
      { label: 'Claude Sonnet 4.6 - Best speed and intelligence balance', value: 'claude-sonnet-4-6' }
    ]
  },
  google: {
    quick: [
      { label: 'Gemini 3.5 Flash - Latest, frontier agentic + coding', value: 'gemini-3.5-flash' },
      { label: 'Gemini 3.1 Flash Lite - Most cost-efficient', value: 'gemini-3.1-flash-lite' },
      { label: 'Gemini 2.5 Flash - Balanced, stable', value: 'gemini-2.5-flash' },
      { label: 'Gemini 2.5 Flash Lite - Fast, low-cost', value: 'gemini-2.5-flash-lite' }
    ],
    deep: [
      { label: 'Gemini 3.1 Pro - Reasoning-first, complex workflows', value: 'gemini-3.1-pro-preview' },
      { label: 'Gemini 3.5 Flash - Latest GA, strong agentic + coding', value: 'gemini-3.5-flash' },
      { label: 'Gemini 2.5 Pro - Stable pro model', value: 'gemini-2.5-pro' },
      { label: 'Gemini 2.5 Flash - Balanced, stable', value: 'gemini-2.5-flash' }
    ]
  },
  xai: {
    quick: [
      { label: 'Grok 4.3 - Latest flagship, fast with built-in reasoning', value: 'grok-4.3' },
      { label: 'Grok Build 0.1 - Coding-specialized, 256K ctx', value: 'grok-build-0.1' },
      { label: 'Grok 4 Fast (Non-Reasoning) - Speed optimized', value: 'grok-4-fast-non-reasoning' }
    ],
    deep: [
      { label: 'Grok 4.3 - Latest flagship, built-in reasoning, 1M ctx', value: 'grok-4.3' },
      { label: 'Grok 4.20 (Reasoning) - Previous-gen reasoning', value: 'grok-4.20-0309-reasoning' },
      { label: 'Grok 4 Fast (Reasoning) - High-performance', value: 'grok-4-fast-reasoning' },
      { label: 'Grok 4 - Flagship (dated build)', value: 'grok-4-0709' }
    ]
  },
  deepseek: {
    quick: [
      { label: 'DeepSeek V4 Flash - Latest V4 fast model', value: 'deepseek-v4-flash' },
      { label: 'DeepSeek V3.2', value: 'deepseek-chat' },
      { label: 'Custom model ID', value: 'custom' }
    ],
    deep: [
      { label: 'DeepSeek V4 Pro - Latest V4 flagship model', value: 'deepseek-v4-pro' },
      { label: 'DeepSeek V3.2 (thinking)', value: 'deepseek-reasoner' },
      { label: 'DeepSeek V3.2', value: 'deepseek-chat' },
      { label: 'Custom model ID', value: 'custom' }
    ]
  },
  qwen: qwenModels,
  'qwen-cn': qwenModels,
  glm: glmModels,
  'glm-cn': glmModels,
  minimax: minimaxModels,
  'minimax-cn': minimaxModels,
  ollama: {
    quick: [
      { label: 'Qwen3:latest (8B)', value: 'qwen3:latest' },
      { label: 'GPT-OSS:latest (20B)', value: 'gpt-oss:latest' },
      { label: 'GLM-4.7-Flash:latest (30B)', value: 'glm-4.7-flash:latest' },
      { label: 'Custom model ID', value: 'custom' }
    ],
    deep: [
      { label: 'GLM-4.7-Flash:latest (30B)', value: 'glm-4.7-flash:latest' },
      { label: 'GPT-OSS:latest (20B)', value: 'gpt-oss:latest' },
      { label: 'Qwen3:latest (8B)', value: 'qwen3:latest' },
      { label: 'Custom model ID', value: 'custom' }
    ]
  },
  openai_compatible: customOnly,
  openrouter: customOnly,
  mistral: customOnly,
  kimi: customOnly,
  groq: customOnly,
  nvidia: customOnly,
  azure: customOnly,
  bedrock: customOnly
}

export function optionsForProvider(provider: string): ProviderModelOptions {
  return modelOptionsByProvider[provider] ?? modelOptionsByProvider.openai
}

export function firstModel(provider: string, mode: 'quick' | 'deep'): string {
  return optionsForProvider(provider)[mode][0]?.value ?? ''
}

export function isKnownProviderModel(provider: string, mode: 'quick' | 'deep', model: string): boolean {
  return optionsForProvider(provider)[mode].some((option) => option.value === model)
}
