# TradingAgents V2

`TradingAgents V2` 是我在原始 `TradingAgents` 引擎基础上扩展的单用户 Web 平台，用来把多智能体分析过程做成一个可运行、可观察、可恢复、可评估的 Agent 系统。

## 我在这个目录里主要做了什么

`v2` 是这个仓库里我个人扩展最集中的部分。这里不是简单包一层页面，而是把原始多智能体流程整理成了更适合展示、调试和继续扩展的工程化运行平台。

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

## 配置提醒

仓库中的 `.env.example` 和默认配置只用于演示结构，不建议直接原样用于本地长期环境。

- 请先复制一份本地 `.env`
- 把数据库账号、密码和应用登录密码改成你自己的值
- API Key 不放在公开仓库中，统一通过本地环境或页面设置注入

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
