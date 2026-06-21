from app.services.tradingagents_runner import TradingAgentsRunner
from app.services.tradingagents_runner import RunExecutionInput


def test_run_execution_input_accepts_rag_contexts():
    run_input = RunExecutionInput(
        run_id="run-1",
        ticker="SPY",
        analysis_date="2026-01-31",
        asset_type="stock",
        selected_analysts=["news"],
        config_snapshot={
            "llm_provider": "deepseek",
            "deep_think_llm": "deepseek-chat",
            "quick_think_llm": "deepseek-chat",
            "output_language": "Chinese",
            "research_depth": 1,
        },
        checkpoint_thread_id="thread-1",
        runtime_api_keys={},
        rag_contexts={"News Analyst": "## Retrieved SPY Evidence"},
    )

    assert run_input.rag_contexts["News Analyst"].startswith("## Retrieved")


def test_messages_from_chunk_streams_agent_level_sections():
    runner = TradingAgentsRunner()

    messages = list(
        runner._messages_from_chunk(
            {
                "investment_debate_state": {
                    "bull_history": "bull partial body",
                }
            },
            {},
        )
    )

    streamed = next(
        message for message in messages if message.event_type == "report_section_streamed"
    )
    assert streamed.report_section == "bull_researcher_report"
    assert streamed.payload["section"] == "bull_researcher_report"
    assert streamed.payload["content_markdown"] == "bull partial body"
    assert streamed.payload["is_partial"] is True


def test_message_from_token_payload_accumulates_agent_tokens():
    runner = TradingAgentsRunner()
    streamed_sections = {}
    stream_state = {"active_section": None}

    first = list(
        runner._messages_from_token_payload(
            ("你", {"langgraph_node": "Market Analyst"}),
            streamed_sections,
            None,
            stream_state,
        )
    )
    second = list(
        runner._messages_from_token_payload(
            ("好", {"langgraph_node": "Market Analyst"}),
            streamed_sections,
            None,
            stream_state,
        )
    )

    assert [message.event_type for message in first] == [
        "agent_started",
        "report_section_streamed",
    ]
    assert first[-1].payload["section"] == "market_report"
    assert first[-1].payload["content_markdown"] == "你"
    assert [message.event_type for message in second] == ["report_section_streamed"]
    assert second[-1].payload["content_markdown"] == "你好"


def test_resolve_stream_input_uses_none_when_resuming_with_checkpoint(monkeypatch):
    runner = TradingAgentsRunner()
    run_input = RunExecutionInput(
        run_id="run-1",
        ticker="NVDA",
        analysis_date="2026-06-19",
        asset_type="stock",
        selected_analysts=["market"],
        config_snapshot={},
        checkpoint_thread_id="thread-1",
        runtime_api_keys={},
        resume_from_checkpoint=True,
    )
    init_state = {"ticker": "NVDA"}

    monkeypatch.setattr(
        "tradingagents.graph.checkpointer.has_checkpoint",
        lambda data_cache_dir, ticker, analysis_date: True,
    )

    stream_input = runner._resolve_stream_input(run_input, ".runtime/tradingagents/cache", init_state)

    assert stream_input is None


def test_resolve_stream_input_keeps_init_state_without_checkpoint(monkeypatch):
    runner = TradingAgentsRunner()
    run_input = RunExecutionInput(
        run_id="run-1",
        ticker="NVDA",
        analysis_date="2026-06-19",
        asset_type="stock",
        selected_analysts=["market"],
        config_snapshot={},
        checkpoint_thread_id="thread-1",
        runtime_api_keys={},
        resume_from_checkpoint=True,
    )
    init_state = {"ticker": "NVDA"}

    monkeypatch.setattr(
        "tradingagents.graph.checkpointer.has_checkpoint",
        lambda data_cache_dir, ticker, analysis_date: False,
    )

    stream_input = runner._resolve_stream_input(run_input, ".runtime/tradingagents/cache", init_state)

    assert stream_input == init_state


def test_message_from_token_payload_skips_already_streamed_prefix():
    runner = TradingAgentsRunner()
    streamed_sections = {"market_report": "你好"}
    replayed_sections = {}
    stream_state = {"active_section": None}

    first = list(
        runner._messages_from_token_payload(
            ("你", {"langgraph_node": "Market Analyst"}),
            streamed_sections,
            replayed_sections,
            stream_state,
        )
    )
    second = list(
        runner._messages_from_token_payload(
            ("好", {"langgraph_node": "Market Analyst"}),
            streamed_sections,
            replayed_sections,
            stream_state,
        )
    )
    third = list(
        runner._messages_from_token_payload(
            ("呀", {"langgraph_node": "Market Analyst"}),
            streamed_sections,
            replayed_sections,
            stream_state,
        )
    )

    assert [message.event_type for message in first] == ["agent_started"]
    assert second == []
    assert [message.event_type for message in third] == ["report_section_streamed"]
    assert third[-1].payload["content_markdown"] == "你好呀"


def test_message_from_token_payload_keeps_old_content_until_resume_output_is_longer():
    runner = TradingAgentsRunner()
    streamed_sections = {"market_report": "old complete"}
    replayed_sections = {}
    stream_state = {"active_section": None}

    first = list(
        runner._messages_from_token_payload(
            ("n", {"langgraph_node": "Market Analyst"}),
            streamed_sections,
            replayed_sections,
            stream_state,
        )
    )
    second = list(
        runner._messages_from_token_payload(
            ("e", {"langgraph_node": "Market Analyst"}),
            streamed_sections,
            replayed_sections,
            stream_state,
        )
    )
    third = list(
        runner._messages_from_token_payload(
            ("w and longer", {"langgraph_node": "Market Analyst"}),
            streamed_sections,
            replayed_sections,
            stream_state,
        )
    )

    assert [message.event_type for message in first] == ["agent_started"]
    assert second == []
    assert [message.event_type for message in third] == ["report_section_streamed"]
    assert third[-1].payload["content_markdown"] == "new and longer"


def test_message_from_token_payload_emits_agent_completed_on_section_switch():
    runner = TradingAgentsRunner()
    streamed_sections = {}
    stream_state = {"active_section": None}

    first_messages = list(
        runner._messages_from_token_payload(
            ("你", {"langgraph_node": "Market Analyst"}),
            streamed_sections,
            None,
            stream_state,
        )
    )
    second_messages = list(
        runner._messages_from_token_payload(
            ("好", {"langgraph_node": "Market Analyst"}),
            streamed_sections,
            None,
            stream_state,
        )
    )
    third_messages = list(
        runner._messages_from_token_payload(
            ("新", {"langgraph_node": "News Analyst"}),
            streamed_sections,
            None,
            stream_state,
        )
    )

    assert [message.event_type for message in first_messages] == [
        "agent_started",
        "report_section_streamed",
    ]
    assert [message.event_type for message in second_messages] == ["report_section_streamed"]
    assert [message.event_type for message in third_messages] == [
        "agent_completed",
        "agent_started",
        "report_section_streamed",
    ]
    assert third_messages[0].agent_name == "Market Analyst"
    assert third_messages[1].agent_name == "News Analyst"
