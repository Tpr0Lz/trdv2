# ECO Agent Trading Project

这是我基于开源 `TradingAgents` 做的一次工程化扩展项目，仓库里包含两部分：

- `TradingAgents/`
  原始多智能体交易研究引擎，以及我在其基础上补充的稳定性修复、RAG 数据样例和相关测试。
- `v2/`
  我围绕 `TradingAgents` 新增的 Web 平台壳层，提供任务创建、实时流式展示、暂停恢复、RAG 证据链、工具调用追踪和质量评估能力。

## My Contributions

如果把这个仓库看成一个完整项目，`v2/` 是我主要补出的工程化部分，也是最适合先看的入口。

- 我把原本偏研究型的多智能体分析流程，扩成了一个可直接演示的 Agent Web 平台
- 我补齐了运行控制台、SSE 流式事件、Pause / Resume、Run History、Trace 和 Quality Gate
- 我为 `SPY` 场景加入了 `RAG` 证据层，让报告能引用结构化市场资料，而不只是依赖在线上下文
- 我额外处理了公开仓库整理，去掉了本地隐私资料和仅适合私有开发环境保留的内容

## 我主要做了什么

这个仓库的重点不是“调用一个大模型 API”，而是把一个研究型多智能体框架，改造成更适合真实演示和工程表达的 Agent 系统。核心扩展包括：

- 基于 `FastAPI + Vue 3 + PostgreSQL + SSE` 搭建 `v2` 运行控制台
- 支持分析任务的创建、历史记录、运行详情、暂停、恢复、取消
- 将报告展示改造成更真实的流式交互，而不是前端打字机式伪流式
- 为 `SPY` 场景加入 `RAG` 证据层，并在报告中用 `[E1] / [E2]` 建立证据引用链
- 增加 `Agent Trace`、`Tool Call Trace`、`Evidence Used`、`Quality Gate` 等可观测与评估能力

## 项目结构

```text
eco_public_release/
  README.md
  TradingAgents/
  v2/
```

## 推荐阅读顺序

如果你想快速理解这个项目，建议按下面顺序看：

1. `v2/README.md`
   先看我做的 Web 平台扩展部分，这是主入口。
2. `v2/backend/app/services/`
   看任务运行、RAG、Trace、Quality Gate 的后端实现。
3. `v2/frontend/src/views/RunDetailView.vue`
   看前端如何展示流式报告、证据和执行轨迹。
4. `TradingAgents/README.md`
   再回头看原始引擎能力和整体背景。

## Acknowledgement

This project is built on top of the open-source `TradingAgents` project by Tauric Research.

- Original project: `https://github.com/TauricResearch/TradingAgents`
- Thanks to the original authors for releasing the multi-agent trading framework and related research work.

我在这个仓库中公开的是基于原项目继续扩展后的工程化版本；原始框架能力和研究背景请以原仓库说明为准。
