from __future__ import annotations

import threading
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler


class ToolTraceCallbackHandler(BaseCallbackHandler):
    """记录 LangChain 工具调用事件，供 runner 按批次持久化。"""

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self._events: list[dict[str, Any]] = []
        self._active_tools: list[dict[str, Any]] = []

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        tool_name = _tool_name(serialized)
        agent_name = _agent_name(kwargs)
        payload = {
            "tool_name": tool_name,
            "input": _preview(input_str),
        }
        with self._lock:
            self._active_tools.append({"tool_name": tool_name, "agent_name": agent_name})
            self._events.append(
                {"event_type": "tool_started", "payload": payload, "agent_name": agent_name}
            )

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        active = self._pop_active_tool()
        payload = {
            "tool_name": active["tool_name"],
            "output_preview": _preview(output),
        }
        with self._lock:
            self._events.append(
                {
                    "event_type": "tool_completed",
                    "payload": payload,
                    "agent_name": active["agent_name"],
                }
            )

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        active = self._pop_active_tool()
        payload = {
            "tool_name": active["tool_name"],
            "error": str(error),
        }
        with self._lock:
            self._events.append(
                {"event_type": "tool_failed", "payload": payload, "agent_name": active["agent_name"]}
            )

    def drain_events(self) -> list[dict[str, Any]]:
        with self._lock:
            events = list(self._events)
            self._events.clear()
            return events

    def _pop_active_tool(self) -> dict[str, Any]:
        with self._lock:
            if self._active_tools:
                return self._active_tools.pop()
        return {"tool_name": "unknown_tool", "agent_name": None}


def _tool_name(serialized: dict[str, Any]) -> str:
    name = serialized.get("name")
    if isinstance(name, str) and name:
        return name
    identifier = serialized.get("id")
    if isinstance(identifier, list) and identifier:
        return str(identifier[-1])
    if isinstance(identifier, str) and identifier:
        return identifier
    return "unknown_tool"


def _agent_name(kwargs: dict[str, Any]) -> str | None:
    metadata = kwargs.get("metadata")
    if isinstance(metadata, dict):
        node_name = metadata.get("langgraph_node") or metadata.get("graph_node")
        if isinstance(node_name, str):
            return node_name
    return None


def _preview(value: Any, limit: int = 500) -> str:
    text = value if isinstance(value, str) else str(value)
    text = text.replace("\r", " ").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit]}[truncated]"
