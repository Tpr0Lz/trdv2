from __future__ import annotations

import os
import sys
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.core.config import get_settings
from app.services.tool_trace_callback import ToolTraceCallbackHandler

API_KEY_ENV_FIELDS = {
    "OPENAI_API_KEY": "openai_api_key",
    "GOOGLE_API_KEY": "google_api_key",
    "ANTHROPIC_API_KEY": "anthropic_api_key",
    "DEEPSEEK_API_KEY": "deepseek_api_key",
    "DASHSCOPE_API_KEY": "dashscope_api_key",
    "ZHIPU_API_KEY": "zhipu_api_key",
    "MINIMAX_API_KEY": "minimax_api_key",
    "OPENROUTER_API_KEY": "openrouter_api_key",
    "ALPHA_VANTAGE_API_KEY": "alpha_vantage_api_key",
    "FRED_API_KEY": "fred_api_key",
}

YFINANCE_PROXY_URL = "http://127.0.0.1:10090"


@dataclass(frozen=True)
class RunExecutionInput:
    run_id: str
    ticker: str
    analysis_date: str
    asset_type: str
    selected_analysts: list[str]
    config_snapshot: dict[str, Any]
    checkpoint_thread_id: str
    runtime_api_keys: dict[str, str]
    resume_from_checkpoint: bool = False
    prior_streamed_sections: dict[str, str] | None = None
    rag_contexts: dict[str, str] | None = None


@dataclass(frozen=True)
class RunnerMessage:
    event_type: str
    payload: dict[str, Any]
    agent_name: str | None = None
    report_section: str | None = None
    report_title: str | None = None
    report_markdown: str | None = None
    metrics: dict[str, Any] | None = None


class TradingAgentsRunner:
    """把 TradingAgents LangGraph stream 适配成 v2 的标准事件。"""

    REPORT_TITLES = {
        "market_report": "Market Analysis",
        "sentiment_report": "Sentiment Analysis",
        "news_report": "News Analysis",
        "fundamentals_report": "Fundamentals Analysis",
        "investment_plan": "Research Team Decision",
        "trader_investment_plan": "Trader Plan",
        "bull_researcher_report": "Bull Researcher",
        "bear_researcher_report": "Bear Researcher",
        "research_manager_report": "Research Manager",
        "trader_report": "Trader",
        "aggressive_analyst_report": "Aggressive Analyst",
        "neutral_analyst_report": "Neutral Analyst",
        "conservative_analyst_report": "Conservative Analyst",
        "portfolio_manager_report": "Portfolio Manager",
        "final_trade_decision": "Final Trade Decision",
        "complete_report": "Complete Report",
    }
    NODE_TO_REPORT_SECTION = {
        "Market Analyst": "market_report",
        "Sentiment Analyst": "sentiment_report",
        "News Analyst": "news_report",
        "Fundamentals Analyst": "fundamentals_report",
        "Bull Researcher": "bull_researcher_report",
        "Bear Researcher": "bear_researcher_report",
        "Research Manager": "research_manager_report",
        "Trader": "trader_report",
        "Aggressive Analyst": "aggressive_analyst_report",
        "Neutral Analyst": "neutral_analyst_report",
        "Conservative Analyst": "conservative_analyst_report",
        "Portfolio Manager": "portfolio_manager_report",
    }

    def run(self, run_input: RunExecutionInput) -> Iterable[RunnerMessage]:
        settings = get_settings()
        project_dir = resolve_tradingagents_project_dir(settings)
        if str(project_dir) not in sys.path:
            sys.path.insert(0, str(project_dir))

        # 中文注释：TradingAgents 依赖环境变量，每次 run 先恢复后端配置里的基线 key。
        export_provider_api_keys(settings)
        # 中文注释：网页 Settings 里的非空 key 再覆盖基线 key，保证用户保存后立即生效。
        apply_runtime_api_keys(run_input.runtime_api_keys)
        prepare_market_data_environment(settings)
        os.environ["TRADINGAGENTS_RESULTS_DIR"] = str(settings.tradingagents_results_dir)
        os.environ["TRADINGAGENTS_CACHE_DIR"] = str(settings.tradingagents_cache_dir)
        os.environ["TRADINGAGENTS_MEMORY_LOG_PATH"] = str(settings.tradingagents_memory_log_path)

        from cli.stats_handler import StatsCallbackHandler
        from tradingagents.default_config import DEFAULT_CONFIG
        from tradingagents.graph.checkpointer import get_checkpointer
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        config = DEFAULT_CONFIG.copy()
        config.update(
            {
                "llm_provider": run_input.config_snapshot["llm_provider"],
                "deep_think_llm": run_input.config_snapshot["deep_think_llm"],
                "quick_think_llm": run_input.config_snapshot["quick_think_llm"],
                "output_language": run_input.config_snapshot["output_language"],
                "max_debate_rounds": run_input.config_snapshot["research_depth"],
                "max_risk_discuss_rounds": run_input.config_snapshot["research_depth"],
                "checkpoint_enabled": True,
                "results_dir": str(settings.tradingagents_results_dir),
                "data_cache_dir": str(settings.tradingagents_cache_dir),
                "memory_log_path": str(settings.tradingagents_memory_log_path),
            }
        )

        stats = StatsCallbackHandler()
        tool_trace = ToolTraceCallbackHandler()
        callbacks = [stats, tool_trace]
        graph = TradingAgentsGraph(
            selected_analysts=run_input.selected_analysts,
            config=config,
            debug=True,
            callbacks=callbacks,
        )
        start_time = time.time()
        past_context = graph.memory_log.get_past_context(run_input.ticker)
        instrument_context = graph.resolve_instrument_context(run_input.ticker, run_input.asset_type)
        init_state = graph.propagator.create_initial_state(
            run_input.ticker,
            run_input.analysis_date,
            asset_type=run_input.asset_type,
            past_context=past_context,
            instrument_context=instrument_context,
            rag_contexts=run_input.rag_contexts or {},
        )
        args = graph.propagator.get_graph_args(callbacks=callbacks)
        args["stream_mode"] = ["values", "messages"]
        args.setdefault("config", {}).setdefault("configurable", {})["thread_id"] = (
            run_input.checkpoint_thread_id
        )

        trace: list[dict[str, Any]] = []
        streamed_sections: dict[str, str] = dict(run_input.prior_streamed_sections or {})
        replayed_sections: dict[str, str] = {}
        stream_state = {"active_section": None}
        with get_checkpointer(config["data_cache_dir"], run_input.ticker) as saver:
            graph.graph = graph.workflow.compile(checkpointer=saver)
            stream_input = self._resolve_stream_input(run_input, config["data_cache_dir"], init_state)
            for mode, payload in graph.graph.stream(stream_input, **args):
                yield from self._messages_from_tool_trace_events(tool_trace.drain_events())
                if mode == "messages":
                    yield from self._messages_from_token_payload(
                        payload,
                        streamed_sections,
                        replayed_sections,
                        stream_state,
                    )
                    continue

                chunk = payload
                trace.append(chunk)
                yield from self._messages_from_chunk(
                    chunk,
                    streamed_sections,
                    replayed_sections,
                )
                if should_finish_macro_run(run_input.asset_type, chunk):
                    # 中文注释：宏观模式只需要 FRED 新闻/宏观报告，避免继续跑交易辩论链。
                    break
            yield from self._messages_from_tool_trace_events(tool_trace.drain_events())

        active_section = stream_state.get("active_section")
        if isinstance(active_section, str):
            yield self._agent_completed_message(active_section)

        final_state: dict[str, Any] = {}
        for chunk in trace:
            final_state.update(chunk)

        complete_report = self._render_complete_report(final_state)
        if complete_report:
            yield RunnerMessage(
                event_type="report_section_updated",
                payload={"section": "complete_report"},
                report_section="complete_report",
                report_title=self.REPORT_TITLES["complete_report"],
                report_markdown=complete_report,
            )
        yield from self._messages_from_agent_sections(final_state)

        if final_state.get("final_trade_decision"):
            graph.memory_log.store_decision(
                ticker=run_input.ticker,
                trade_date=run_input.analysis_date,
                final_trade_decision=final_state["final_trade_decision"],
            )

        current_stats = stats.get_stats()
        yield RunnerMessage(
            event_type="metric_updated",
            payload=current_stats,
            metrics={
                "llm_calls": current_stats["llm_calls"],
                "tool_calls": current_stats["tool_calls"],
                "tokens_in": current_stats["tokens_in"],
                "tokens_out": current_stats["tokens_out"],
                "elapsed_seconds": int(time.time() - start_time),
                "analyst_wall_times": {},
            },
        )

    def _resolve_stream_input(
        self,
        run_input: RunExecutionInput,
        data_cache_dir: str,
        init_state: dict[str, Any],
    ) -> dict[str, Any] | None:
        """中文注释：checkpoint 恢复时传 None，避免 LangGraph 把恢复执行当成新 run 重开。"""
        if not run_input.resume_from_checkpoint:
            return init_state

        from tradingagents.graph.checkpointer import has_checkpoint

        if has_checkpoint(data_cache_dir, run_input.ticker, run_input.analysis_date):
            return None
        return init_state

    def _messages_from_chunk(
        self,
        chunk: dict[str, Any],
        streamed_sections: dict[str, str],
        replayed_sections: dict[str, str] | None = None,
    ) -> Iterable[RunnerMessage]:
        for section, title in self.REPORT_TITLES.items():
            if section in ("complete_report", "risk_debate"):
                continue
            content = chunk.get(section)
            if isinstance(content, str) and content.strip():
                next_content = self._merge_resumed_content(
                    section,
                    content,
                    streamed_sections,
                    replayed_sections,
                )
                if next_content is None:
                    continue
                streamed_sections[section] = next_content
                yield RunnerMessage(
                    event_type="report_section_streamed",
                    payload={
                        "section": section,
                        "title": title,
                        "content_markdown": next_content,
                        "is_partial": True,
                    },
                    report_section=section,
                    report_title=title,
                    report_markdown=next_content,
                )

        debate = chunk.get("risk_debate_state")
        if isinstance(debate, dict) and debate.get("history"):
            next_debate = self._merge_resumed_content(
                "risk_debate",
                debate["history"],
                streamed_sections,
                replayed_sections,
            )
            if next_debate is None:
                return
            streamed_sections["risk_debate"] = next_debate
            yield RunnerMessage(
                event_type="report_section_streamed",
                payload={
                    "section": "risk_debate",
                    "title": "Risk Debate",
                    "content_markdown": next_debate,
                    "is_partial": True,
                },
                report_section="risk_debate",
                report_title="Risk Debate",
                report_markdown=next_debate,
            )
        yield from self._messages_from_agent_sections(
            chunk,
            event_type="report_section_streamed",
            streamed_sections=streamed_sections,
        )

    def _messages_from_tool_trace_events(
        self,
        events: list[dict[str, Any]],
    ) -> Iterable[RunnerMessage]:
        for event in events:
            yield RunnerMessage(
                event_type=event["event_type"],
                payload=event["payload"],
                agent_name=event.get("agent_name"),
            )

    def _messages_from_token_payload(
        self,
        payload: tuple[Any, dict[str, Any]],
        streamed_sections: dict[str, str],
        replayed_sections: dict[str, str] | None = None,
        stream_state: dict[str, str | None] | None = None,
    ) -> Iterable[RunnerMessage]:
        token, metadata = payload
        section = self._report_section_from_metadata(metadata)
        if not section:
            return []

        normalized_token = self._normalize_stream_token(token)
        if not normalized_token:
            return []

        messages: list[RunnerMessage] = []
        active_section = stream_state.get("active_section") if stream_state is not None else None
        if active_section != section:
            if isinstance(active_section, str):
                messages.append(self._agent_completed_message(active_section))
            messages.append(self._agent_started_message(section))
            if stream_state is not None:
                stream_state["active_section"] = section

        if replayed_sections is None:
            next_content = streamed_sections.get(section, "") + normalized_token
            streamed_sections[section] = next_content
            messages.append(
                RunnerMessage(
                    event_type="report_section_streamed",
                    payload={
                        "section": section,
                        "title": self.REPORT_TITLES[section],
                        "content_markdown": next_content,
                        "is_partial": True,
                    },
                    agent_name=self._agent_name_from_section(section),
                    report_section=section,
                    report_title=self.REPORT_TITLES[section],
                    report_markdown=next_content,
                )
            )
            return messages

        replayed_content = (replayed_sections or {}).get(section, "") + normalized_token
        if replayed_sections is not None:
            replayed_sections[section] = replayed_content
        next_content = self._merge_resumed_content(
            section,
            replayed_content,
            streamed_sections,
            replayed_sections=None,
        )
        if next_content is None:
            return messages
        streamed_sections[section] = next_content
        messages.append(
            RunnerMessage(
                event_type="report_section_streamed",
                payload={
                    "section": section,
                    "title": self.REPORT_TITLES[section],
                    "content_markdown": next_content,
                    "is_partial": True,
                },
                agent_name=self._agent_name_from_section(section),
                report_section=section,
                report_title=self.REPORT_TITLES[section],
                report_markdown=next_content,
            )
        )
        return messages

    def _merge_resumed_content(
        self,
        section: str,
        incoming_content: str,
        streamed_sections: dict[str, str],
        replayed_sections: dict[str, str] | None,
    ) -> str | None:
        previous_content = streamed_sections.get(section, "")
        if replayed_sections is not None:
            replayed_sections[section] = incoming_content
        if not previous_content:
            return incoming_content
        # 中文注释：恢复阶段在新内容真正超过旧内容前，始终保留旧内容，避免前端先清空再重刷。
        if len(incoming_content) <= len(previous_content):
            return None
        return incoming_content

    def _messages_from_agent_sections(
        self,
        state: dict[str, Any],
        event_type: str = "report_section_updated",
        streamed_sections: dict[str, str] | None = None,
    ) -> Iterable[RunnerMessage]:
        for section, content in build_agent_report_sections(state).items():
            if event_type == "report_section_streamed" and streamed_sections is not None:
                if streamed_sections.get(section) == content:
                    continue
                streamed_sections[section] = content
            yield RunnerMessage(
                event_type=event_type,
                payload={
                    "section": section,
                    "title": self.REPORT_TITLES[section],
                    "content_markdown": content,
                    "is_partial": event_type == "report_section_streamed",
                },
                report_section=section,
                report_title=self.REPORT_TITLES[section],
                report_markdown=content,
            )

    def _report_section_from_metadata(self, metadata: dict[str, Any]) -> str | None:
        node_name = metadata.get("langgraph_node") or metadata.get("graph_node")
        if not isinstance(node_name, str):
            return None
        return self.NODE_TO_REPORT_SECTION.get(node_name)

    def _normalize_stream_token(self, token: Any) -> str:
        if isinstance(token, str):
            return token
        content = getattr(token, "content", None)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        return ""

    def _agent_name_from_section(self, section: str) -> str | None:
        for node_name, report_section in self.NODE_TO_REPORT_SECTION.items():
            if report_section == section:
                return node_name
        return None

    def _agent_started_message(self, section: str) -> RunnerMessage:
        return RunnerMessage(
            event_type="agent_started",
            payload={"section": section, "title": self.REPORT_TITLES[section]},
            agent_name=self._agent_name_from_section(section),
            report_section=section,
            report_title=self.REPORT_TITLES[section],
        )

    def _agent_completed_message(self, section: str) -> RunnerMessage:
        return RunnerMessage(
            event_type="agent_completed",
            payload={"section": section, "title": self.REPORT_TITLES[section]},
            agent_name=self._agent_name_from_section(section),
            report_section=section,
            report_title=self.REPORT_TITLES[section],
        )

    def _render_complete_report(self, final_state: dict[str, Any]) -> str:
        parts: list[str] = []
        section_order = [
            ("market_report", "Market Analysis"),
            ("sentiment_report", "Sentiment Analysis"),
            ("news_report", "News Analysis"),
            ("fundamentals_report", "Fundamentals Analysis"),
            ("investment_plan", "Research Team Decision"),
            ("trader_investment_plan", "Trader Plan"),
            ("final_trade_decision", "Final Trade Decision"),
        ]
        for key, title in section_order:
            content = final_state.get(key)
            if isinstance(content, str) and content.strip():
                parts.append(f"## {title}\n\n{content}")
        return "\n\n".join(parts)


def export_provider_api_keys(settings: object) -> None:
    """把 .env 中的模型/数据源 key 补到进程环境，供 TradingAgents 原代码读取。"""
    for env_name, field_name in API_KEY_ENV_FIELDS.items():
        value = getattr(settings, field_name, None)
        normalized = value.strip() if isinstance(value, str) else ""
        if normalized:
            os.environ[env_name] = normalized
        else:
            os.environ.pop(env_name, None)


def apply_runtime_api_keys(api_keys: dict[str, str]) -> None:
    """应用网页 Settings 保存的运行时 key，只覆盖用户实际填写的值。"""
    for env_name, value in api_keys.items():
        normalized = value.strip()
        if normalized:
            os.environ[env_name] = normalized


def should_finish_macro_run(asset_type: str, chunk: dict[str, Any]) -> bool:
    """宏观模式拿到 news_report 后即可完成，不进入股票交易决策链。"""
    report = chunk.get("news_report")
    return asset_type == "macro" and isinstance(report, str) and bool(report.strip())


def prepare_market_data_environment(settings: object) -> Path:
    """准备行情数据运行环境，避免继承不可用代理和 yfinance 默认缓存目录。"""
    clear_dead_local_proxy_env()
    force_yfinance_proxy()
    cache_dir = (Path(getattr(settings, "tradingagents_cache_dir")) / "yfinance").resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)

    import yfinance as yf
    import yfinance.cache as yf_cache

    # 中文注释：yfinance 1.4.x 不只会写时区缓存，还会写 cookies/isin sqlite 缓存。
    # 如果只重定向 tz cache，其他 sqlite 仍可能落到用户目录并触发 unable to open database file。
    yf.set_tz_cache_location(str(cache_dir))
    yf_cache.set_cache_location(str(cache_dir))
    return cache_dir


def clear_dead_local_proxy_env() -> None:
    """清理 Codex/本地进程可能继承的 127.0.0.1:9 空代理。"""
    proxy_names = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ]
    for name in proxy_names:
        value = os.environ.get(name)
        if value and _is_dead_local_proxy(value):
            os.environ.pop(name, None)


def force_yfinance_proxy() -> None:
    """中文注释：Yahoo Finance 请求统一走 127.0.0.1:10090，降低本机网络环境差异影响。"""
    proxy_names = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ]
    for name in proxy_names:
        os.environ[name] = YFINANCE_PROXY_URL


def _is_dead_local_proxy(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.hostname in {"127.0.0.1", "localhost"} and parsed.port == 9


def build_agent_report_sections(state: dict[str, Any]) -> dict[str, str]:
    """从 TradingAgents state 中提取可单独展示的 agent 级报告。"""
    sections: dict[str, str] = {}
    research_state = state.get("investment_debate_state")
    if isinstance(research_state, dict):
        _set_non_empty_report(sections, "bull_researcher_report", research_state.get("bull_history"))
        _set_non_empty_report(sections, "bear_researcher_report", research_state.get("bear_history"))
        _set_non_empty_report(
            sections,
            "research_manager_report",
            research_state.get("judge_decision"),
        )

    _set_non_empty_report(sections, "trader_report", state.get("trader_investment_plan"))

    risk_state = state.get("risk_debate_state")
    if isinstance(risk_state, dict):
        _set_non_empty_report(
            sections,
            "aggressive_analyst_report",
            risk_state.get("aggressive_history"),
        )
        _set_non_empty_report(
            sections,
            "neutral_analyst_report",
            risk_state.get("neutral_history"),
        )
        _set_non_empty_report(
            sections,
            "conservative_analyst_report",
            risk_state.get("conservative_history"),
        )

    _set_non_empty_report(
        sections,
        "portfolio_manager_report",
        state.get("final_trade_decision"),
    )
    return sections


def _set_non_empty_report(target: dict[str, str], section: str, value: Any) -> None:
    """中文注释：只持久化真正有内容的 agent 报告，避免空字符串污染详情页。"""
    if isinstance(value, str) and value.strip():
        target[section] = value


def resolve_tradingagents_project_dir(settings: object) -> Path:
    """校验 TradingAgents 源码目录，避免后续导入 cli 时才暴露模糊错误。"""
    project_dir = Path(getattr(settings, "tradingagents_project_dir")).resolve()
    if not (project_dir / "cli" / "stats_handler.py").exists():
        raise RuntimeError(f"TradingAgents 项目目录无效: {project_dir}")
    return project_dir
