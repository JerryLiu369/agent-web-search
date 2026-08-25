import json

import pytest

from agent_web_search import mcp
from agent_web_search.mcp import ALL_PROVIDERS_FAILED_CODE, format_mcp_result
from agent_web_search.models import ProviderResponse, SearchResponse


def test_mcp_result_is_an_error_when_all_providers_fail():
    response = SearchResponse(
        query="latest news",
        providers={},
        failed_provider_errors={
            "ark": "ARK_API_KEY is not set",
            "ddgs": "DDGS TimeoutError: timed out",
        },
    )

    text, is_error = format_mcp_result(response)
    payload = json.loads(text)

    assert is_error is True
    assert payload == {
        "error": {
            "code": ALL_PROVIDERS_FAILED_CODE,
            "message": (
                "All enabled search providers failed. Check provider "
                "configuration, credentials, quotas, and network access."
            ),
            "provider_errors": {
                "ark": "ARK_API_KEY is not set",
                "ddgs": "DDGS TimeoutError: timed out",
            },
        },
        "query": "latest news",
    }


def test_mcp_result_stays_successful_when_one_provider_succeeds():
    response = SearchResponse(
        query="latest news",
        providers={"ddgs": ProviderResponse(provider="ddgs", searched=True)},
        failed_provider_errors={"ark": "ARK_API_KEY is not set"},
    )

    text, is_error = format_mcp_result(response)
    payload = json.loads(text)

    assert is_error is False
    assert list(payload["providers"]) == ["ddgs"]
    assert "ark" not in text


def test_mcp_command_defaults_to_stdio(monkeypatch):
    called = []

    async def fake_run_stdio():
        called.append("stdio")

    monkeypatch.delenv("AGENT_WEB_SEARCH_MCP_TRANSPORT", raising=False)
    monkeypatch.setattr(mcp, "run_stdio", fake_run_stdio)

    mcp.main([])

    assert called == ["stdio"]


def test_mcp_command_selects_http_from_environment(monkeypatch):
    from agent_web_search import mcp_http

    called = []
    monkeypatch.setenv("AGENT_WEB_SEARCH_MCP_TRANSPORT", "http")
    monkeypatch.setattr(mcp_http, "run_http", lambda: called.append("http"))

    mcp.main([])

    assert called == ["http"]


def test_mcp_command_rejects_an_unknown_environment_transport(monkeypatch):
    monkeypatch.setenv("AGENT_WEB_SEARCH_MCP_TRANSPORT", "websocket")

    with pytest.raises(SystemExit) as exc_info:
        mcp.main([])

    assert exc_info.value.code == 2
