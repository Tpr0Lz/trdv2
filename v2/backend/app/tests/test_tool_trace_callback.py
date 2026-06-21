from app.services.tool_trace_callback import ToolTraceCallbackHandler


def test_tool_trace_callback_records_tool_start_and_end():
    callback = ToolTraceCallbackHandler()

    callback.on_tool_start({"name": "get_news"}, "SPY macro news", run_id="tool-run-1")
    callback.on_tool_end("3 articles", run_id="tool-run-1")

    events = callback.drain_events()

    assert [event["event_type"] for event in events] == ["tool_started", "tool_completed"]
    assert events[0]["agent_name"] is None
    assert events[0]["payload"]["tool_name"] == "get_news"
    assert events[0]["payload"]["input"] == "SPY macro news"
    assert events[1]["payload"]["tool_name"] == "get_news"
    assert events[1]["payload"]["output_preview"] == "3 articles"


def test_tool_trace_callback_records_tool_error():
    callback = ToolTraceCallbackHandler()

    callback.on_tool_start({"id": ["pkg", "search_tool"]}, "SPY", run_id="tool-run-1")
    callback.on_tool_error(RuntimeError("network failed"), run_id="tool-run-1")

    events = callback.drain_events()

    assert [event["event_type"] for event in events] == ["tool_started", "tool_failed"]
    assert events[0]["payload"]["tool_name"] == "search_tool"
    assert events[1]["payload"]["error"] == "network failed"


def test_tool_trace_callback_drain_returns_each_event_once():
    callback = ToolTraceCallbackHandler()

    callback.on_tool_start({"name": "get_price"}, "SPY", run_id="tool-run-1")

    assert len(callback.drain_events()) == 1
    assert callback.drain_events() == []
