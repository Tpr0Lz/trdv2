# TradingAgents V2

`TradingAgents V2` 是我在原始 `TradingAgents` 引擎基础上扩展的单用户 Web 平台，用来把多智能体分析过程做成一个可运行、可观察、可恢复、可评估的 Agent 系统。

## 这个版本重点解决什么问题

原始 `TradingAgents` 更偏研究型框架，核心价值在于多智能体协作分析。  
而 `v2` 重点补的是工程化平台能力：

- 登录和单用户任务管理
- 创建后台分析任务
- 基于 `SSE` 的实时流式事件展示
- `PostgreSQL` 持久化事件、报告、指标和证据
- 后端中断后的手动恢复
- `SPY` 场景下的 `RAG` 证据链
- `Agent Trace`、`Tool Call Trace`、`Quality Gate`

## 技术栈

- Backend: `FastAPI`, `SQLAlchemy`, `Alembic`, `PostgreSQL`
- Frontend: `Vue 3`, `Vite`, `TypeScript`, `Pinia`, `Naive UI`
- Agent runtime: `TradingAgents`, `LangGraph`
- Streaming: `SSE / EventSource`

## 本目录结构

```text
v2/
  backend/
  frontend/
  docker-compose.yml
  .env.example
```

## 本地数据库

先用 Docker 启动 PostgreSQL：

```powershell
docker compose up -d postgres
```

数据库使用 `localhost:54329`，避免和本机默认 `5432` 冲突。

## 后端启动

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

## 前端启动

```powershell
cd frontend
npm install
npm run dev
```

## 致谢

This web platform is built around the open-source `TradingAgents` engine.

- Original project: `https://github.com/TauricResearch/TradingAgents`

`v2` 这一层的 Web 平台壳、运行控制台、流式展示、RAG 证据链和可观测能力，是我在原始引擎基础上继续扩展完成的。
