import os
import tomllib
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.tradingagents_runner import (
    apply_runtime_api_keys,
    build_agent_report_sections,
    clear_dead_local_proxy_env,
    export_provider_api_keys,
    prepare_market_data_environment,
    resolve_tradingagents_project_dir,
)


def test_backend_package_installs_local_tradingagents_dependency():
    """中文注释：后端安装时必须连同本地 TradingAgents 包及其三方依赖一起安装。"""
    pyproject_path = (
        __file__
        .replace("app\\tests\\test_tradingagents_runner_env.py", "pyproject.toml")
    )
    with open(pyproject_path, "rb") as file:
        pyproject = tomllib.load(file)

    dependencies = pyproject["project"]["dependencies"]

    assert any(
        dependency.startswith("tradingagents @ file:///") and "TradingAgents" in dependency
        for dependency in dependencies
    )


def test_export_provider_api_keys_sets_deepseek_key_from_settings(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    settings = SimpleNamespace(deepseek_api_key="sk-test-deepseek")

    export_provider_api_keys(settings)

    assert os.environ["DEEPSEEK_API_KEY"] == "sk-test-deepseek"


def test_export_provider_api_keys_restores_backend_env_value(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-from-previous-run")
    settings = SimpleNamespace(deepseek_api_key="sk-from-env-file")

    export_provider_api_keys(settings)

    assert os.environ["DEEPSEEK_API_KEY"] == "sk-from-env-file"


def test_resolve_tradingagents_project_dir_rejects_invalid_path(tmp_path):
    settings = SimpleNamespace(tradingagents_project_dir=tmp_path)

    with pytest.raises(RuntimeError, match="TradingAgents 项目目录无效"):
        resolve_tradingagents_project_dir(settings)


def test_apply_runtime_api_keys_overrides_existing_process_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-old")

    apply_runtime_api_keys({"DEEPSEEK_API_KEY": "sk-from-web-settings"})

    assert os.environ["DEEPSEEK_API_KEY"] == "sk-from-web-settings"


def test_apply_runtime_api_keys_keeps_backend_env_for_empty_web_setting(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "fred-old")

    apply_runtime_api_keys({"FRED_API_KEY": ""})

    assert os.environ["FRED_API_KEY"] == "fred-old"


def test_clear_dead_local_proxy_env_removes_port_9_proxy(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("HTTPS_PROXY", "http://localhost:9")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:7890")

    clear_dead_local_proxy_env()

    assert "HTTP_PROXY" not in os.environ
    assert "HTTPS_PROXY" not in os.environ
    assert os.environ["ALL_PROXY"] == "http://127.0.0.1:7890"


def test_prepare_market_data_environment_sets_yfinance_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    settings = SimpleNamespace(tradingagents_cache_dir=tmp_path)

    with patch("yfinance.set_tz_cache_location") as set_tz_cache_location, patch(
        "yfinance.cache.set_cache_location"
    ) as set_cache_location:
        cache_dir = prepare_market_data_environment(settings)

    assert cache_dir == tmp_path / "yfinance"
    assert cache_dir.exists()
    assert os.environ["HTTP_PROXY"] == "http://127.0.0.1:10090"
    assert os.environ["HTTPS_PROXY"] == "http://127.0.0.1:10090"
    assert os.environ["ALL_PROXY"] == "http://127.0.0.1:10090"
    set_tz_cache_location.assert_called_once_with(str(cache_dir))
    set_cache_location.assert_called_once_with(str(cache_dir))


def test_prepare_market_data_environment_overrides_existing_proxy_to_10090(tmp_path, monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:7890")
    monkeypatch.setenv("HTTPS_PROXY", "http://localhost:8080")
    monkeypatch.setenv("ALL_PROXY", "socks5://127.0.0.1:1080")
    settings = SimpleNamespace(tradingagents_cache_dir=tmp_path)

    with patch("yfinance.set_tz_cache_location"), patch("yfinance.cache.set_cache_location"):
        prepare_market_data_environment(settings)

    assert os.environ["HTTP_PROXY"] == "http://127.0.0.1:10090"
    assert os.environ["HTTPS_PROXY"] == "http://127.0.0.1:10090"
    assert os.environ["ALL_PROXY"] == "http://127.0.0.1:10090"
    assert os.environ["http_proxy"] == "http://127.0.0.1:10090"
    assert os.environ["https_proxy"] == "http://127.0.0.1:10090"
    assert os.environ["all_proxy"] == "http://127.0.0.1:10090"


def test_build_agent_report_sections_extracts_research_risk_and_portfolio_agents():
    final_state = {
        "investment_debate_state": {
            "bull_history": "bull case",
            "bear_history": "bear case",
            "judge_decision": "research decision",
        },
        "trader_investment_plan": "trader plan",
        "risk_debate_state": {
            "aggressive_history": "aggressive view",
            "neutral_history": "neutral view",
            "conservative_history": "conservative view",
        },
        "final_trade_decision": "portfolio decision",
    }

    sections = build_agent_report_sections(final_state)

    assert sections["bull_researcher_report"] == "bull case"
    assert sections["bear_researcher_report"] == "bear case"
    assert sections["research_manager_report"] == "research decision"
    assert sections["trader_report"] == "trader plan"
    assert sections["aggressive_analyst_report"] == "aggressive view"
    assert sections["neutral_analyst_report"] == "neutral view"
    assert sections["conservative_analyst_report"] == "conservative view"
    assert sections["portfolio_manager_report"] == "portfolio decision"


def test_build_agent_report_sections_skips_blank_values():
    final_state = {
        "investment_debate_state": {
            "bull_history": "  ",
            "bear_history": "",
            "judge_decision": "research decision",
        },
        "trader_investment_plan": "",
        "risk_debate_state": {
            "aggressive_history": None,
            "neutral_history": "neutral view",
            "conservative_history": " ",
        },
        "final_trade_decision": "portfolio decision",
    }

    sections = build_agent_report_sections(final_state)

    assert sections == {
        "research_manager_report": "research decision",
        "neutral_analyst_report": "neutral view",
        "portfolio_manager_report": "portfolio decision",
    }
