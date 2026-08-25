from __future__ import annotations

import importlib
import sys
from typing import ClassVar

import pytest
from starlette.testclient import TestClient

from agent_web_search.mcp import create_mcp_server
from agent_web_search.mcp_http import HTTPSettings, create_http_app
from agent_web_search.models import ProviderResponse, SearchResponse

TOKEN = "test-token-with-at-least-32-characters"
MCP_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": "2025-06-18",
}
TOOLS_LIST = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {},
}


class _Engine:
    enabled_provider_names: ClassVar[list[str]] = ["ddgs", "exa", "parallel"]

    def __init__(self, response: SearchResponse | None = None):
        self.response = response

    def search(self, request):
        if self.response is not None:
            return self.response
        return SearchResponse(
            query=request.query,
            providers={
                "ddgs": ProviderResponse(provider="ddgs", searched=True),
            },
        )


def _settings(
    *,
    token: str = TOKEN,
    allow_anonymous: bool = False,
) -> HTTPSettings:
    return HTTPSettings(
        host="testserver",
        port=8000,
        auth_token=token,
        allow_anonymous=allow_anonymous,
        allowed_hosts=(),
        allowed_origins=(),
        log_level="info",
    )


def _app(settings: HTTPSettings, engine: _Engine | None = None):
    return create_http_app(
        settings=settings,
        server=create_mcp_server(engine or _Engine()),
    )


def test_http_settings_use_platform_port_and_env_only_configuration():
    settings = HTTPSettings.from_env(
        {
            "PORT": "9123",
            "AGENT_WEB_SEARCH_AUTH_TOKEN": TOKEN,
            "AGENT_WEB_SEARCH_HTTP_ALLOWED_HOSTS": "search.example.com,localhost:*",
            "AGENT_WEB_SEARCH_HTTP_ALLOWED_ORIGINS": "https://search.example.com",
        }
    )

    assert settings.host == "0.0.0.0"
    assert settings.port == 9123
    assert settings.allowed_hosts == ("search.example.com", "localhost:*")
    assert settings.allowed_origins == ("https://search.example.com",)


def test_http_requires_a_strong_token_by_default():
    with pytest.raises(ValueError, match="requires AGENT_WEB_SEARCH_AUTH_TOKEN"):
        _app(_settings(token=""))

    with pytest.raises(ValueError, match="at least 32 characters"):
        _app(_settings(token="too-short"))


def test_health_check_is_public_but_mcp_requires_bearer_token():
    with TestClient(_app(_settings())) as client:
        health = client.get("/healthz")
        missing = client.post("/mcp", headers=MCP_HEADERS, json=TOOLS_LIST)
        invalid = client.post(
            "/mcp",
            headers={**MCP_HEADERS, "Authorization": "Bearer wrong-token"},
            json=TOOLS_LIST,
        )

    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "transport": "streamable-http",
        "stateless": True,
    }
    assert missing.status_code == 401
    assert invalid.status_code == 401


def test_authenticated_http_exposes_shared_tool_schema_without_a_session():
    with TestClient(_app(_settings())) as client:
        response = client.post(
            "/mcp",
            headers={**MCP_HEADERS, "Authorization": f"Bearer {TOKEN}"},
            json=TOOLS_LIST,
        )

    assert response.status_code == 200
    assert "MCP-Session-Id" not in response.headers
    tool = response.json()["result"]["tools"][0]
    assert tool["name"] == "web_search"
    assert tool["inputSchema"]["properties"]["providers"]["items"]["enum"] == [
        "ddgs",
        "exa",
        "parallel",
    ]


def test_stateless_json_mode_does_not_open_an_sse_get_stream():
    with TestClient(_app(_settings())) as client:
        response = client.get(
            "/mcp",
            headers={
                "Accept": "text/event-stream",
                "Authorization": f"Bearer {TOKEN}",
            },
        )

    assert response.status_code == 405


def test_anonymous_http_requires_an_explicit_opt_out():
    with TestClient(_app(_settings(token="", allow_anonymous=True))) as client:
        response = client.post("/mcp", headers=MCP_HEADERS, json=TOOLS_LIST)

    assert response.status_code == 200


def test_vercel_entrypoint_exports_the_same_asgi_app(monkeypatch):
    monkeypatch.setenv("AGENT_WEB_SEARCH_AUTH_TOKEN", TOKEN)
    sys.modules.pop("agent_web_search.vercel", None)

    module = importlib.import_module("agent_web_search.vercel")
    with TestClient(module.app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["stateless"] is True


def test_http_tool_call_uses_the_shared_success_shape():
    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "web_search",
            "arguments": {"query": "latest news"},
        },
    }
    with TestClient(_app(_settings())) as client:
        response = client.post(
            "/mcp",
            headers={**MCP_HEADERS, "Authorization": f"Bearer {TOKEN}"},
            json=request,
        )

    result = response.json()["result"]
    assert response.status_code == 200
    assert result["isError"] is False
    assert '"query": "latest news"' in result["content"][0]["text"]


def test_http_preserves_all_provider_failure_as_a_tool_error():
    failed = SearchResponse(
        query="latest news",
        providers={},
        failed_provider_errors={"ddgs": "timed out"},
    )
    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "web_search",
            "arguments": {"query": "latest news"},
        },
    }
    with TestClient(_app(_settings(), _Engine(failed))) as client:
        response = client.post(
            "/mcp",
            headers={**MCP_HEADERS, "Authorization": f"Bearer {TOKEN}"},
            json=request,
        )

    result = response.json()["result"]
    assert response.status_code == 200
    assert result["isError"] is True
    assert '"code": "all_providers_failed"' in result["content"][0]["text"]
