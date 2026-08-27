import json
from typing import ClassVar

import pytest

from agent_web_search import mcp
from agent_web_search.mcp import format_mcp_result
from agent_web_search.models import ProviderResponse, SearchResponse
from agent_web_search.output import ALL_PROVIDERS_FAILED_CODE


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


def _call_web_search(server, arguments):
    """Invoke the shared stdio tools/call handler directly."""
    import asyncio

    import mcp_types as types

    async def run():
        entry = server._request_handlers["tools/call"]
        return await entry.handler(
            None, types.CallToolRequestParams(name="web_search", arguments=arguments)
        )

    return asyncio.run(run())


class _StubEngine:
    enabled_provider_names: ClassVar[list[str]] = ["ddgs", "exa", "parallel"]

    def search(self, request):
        from agent_web_search.models import ProviderResponse, SearchResponse

        return SearchResponse(
            query=request.query,
            providers={"ddgs": ProviderResponse(provider="ddgs", searched=True)},
        )


def test_stdio_rejects_invalid_arguments_as_a_tool_error():
    server = mcp.create_mcp_server(_StubEngine())

    result = _call_web_search(server, {"query": "hi", "providers": ["nope"]})
    payload = json.loads(result.content[0].text)

    assert result.is_error is True
    assert payload["error"]["code"] == "invalid_arguments"
    assert any("not enabled" in d for d in payload["error"]["details"])


def test_stdio_rejects_string_providers_as_a_tool_error():
    server = mcp.create_mcp_server(_StubEngine())

    result = _call_web_search(server, {"query": "hi", "providers": "ddgs"})
    payload = json.loads(result.content[0].text)

    assert result.is_error is True
    assert payload["error"]["code"] == "invalid_arguments"
    assert any("array" in d for d in payload["error"]["details"])


def test_stdio_rejects_unknown_arguments():
    server = mcp.create_mcp_server(_StubEngine())

    result = _call_web_search(server, {"query": "hi", "bogus": 1})
    payload = json.loads(result.content[0].text)

    assert result.is_error is True
    assert any("unknown argument" in d for d in payload["error"]["details"])


def test_stdio_empty_query_is_a_tool_error_not_a_protocol_error():
    server = mcp.create_mcp_server(_StubEngine())

    for arguments in ({"query": ""}, {"query": "   "}, {}):
        result = _call_web_search(server, arguments)
        payload = json.loads(result.content[0].text)
        assert result.is_error is True
        assert payload["error"]["code"] == "invalid_arguments"


def test_stdio_valid_arguments_still_succeed():
    server = mcp.create_mcp_server(_StubEngine())

    result = _call_web_search(server, {"query": "latest news"})
    payload = json.loads(result.content[0].text)

    assert result.is_error is False
    assert '"query": "latest news"' in result.content[0].text
    assert list(payload["providers"]) == ["ddgs"]
