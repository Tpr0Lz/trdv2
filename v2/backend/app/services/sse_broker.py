from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncGenerator
from threading import Lock

from app.schemas.events import RunEventResponse


class RunEventBroker:
    """进程内 SSE 分发器；数据库仍是事件事实来源。"""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[RunEventResponse]]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = Lock()

    async def subscribe(self, run_id: str) -> AsyncGenerator[RunEventResponse, None]:
        with self._lock:
            if self._loop is None:
                self._loop = asyncio.get_running_loop()
        queue: asyncio.Queue[RunEventResponse] = asyncio.Queue()
        with self._lock:
            self._subscribers[run_id].add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            with self._lock:
                self._subscribers[run_id].discard(queue)

    def publish(self, event: RunEventResponse) -> None:
        with self._lock:
            loop = self._loop
            queues = list(self._subscribers.get(event.run_id, set()))
        if loop is None:
            return
        for queue in queues:
            # 中文注释：worker 线程里发事件时，切回订阅所在线程的事件循环再投递。
            loop.call_soon_threadsafe(queue.put_nowait, event)


broker = RunEventBroker()
