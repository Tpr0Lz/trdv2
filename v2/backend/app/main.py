import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.rag import router as rag_router
from app.api.runs import router as runs_router
from app.api.settings import router as settings_router
from app.workers.inprocess_manager import InProcessRunManager


def create_app(run_manager: InProcessRunManager | None = None) -> FastAPI:
    """创建 FastAPI 应用，后续在这里挂载路由和启动钩子。"""
    manager = run_manager or InProcessRunManager()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # 中文注释：启动阶段只派发后台恢复任务，避免同步恢复阻塞应用 ready。
        asyncio.create_task(asyncio.to_thread(app.state.run_manager.mark_running_runs_interrupted_on_startup))
        yield

    app = FastAPI(title="TradingAgents V2 API", lifespan=lifespan)
    app.state.run_manager = manager

    @app.get("/health")
    def health() -> dict[str, str]:
        """给本地开发和部署探针使用的最小健康检查。"""
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(rag_router)
    app.include_router(runs_router)
    app.include_router(settings_router)

    return app


app = create_app()
