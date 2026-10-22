import json
import urllib.error
import urllib.request

import pytest

from agent_web_search.engine import SearchEngine
from agent_web_search.models import SearchRequest
from agent_web_search.output import search_result_payload
from agent_web_search.providers.parallel import (
    ENDPOINT,
    MCP_ENDPOINT,
    MCP_PROTOCOL_VERSION,
    USER_AGENT,
    ParallelProvider,
)


class _Response:
    def __init__(self, data=None, *, text=None, headers=None):
        self.data = data
        self.text = text
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        if self.text is not None:
            return self.text.encode()
        return json.dumps(self.data).encode()


@pytest.mark.parametrize("encoding", ["json", "sse"])
def test_parallel_without_key_uses_free_mcp(monkeypatch, encoding):
    captured = []

    def fake_urlopen(request, timeout=None):
        headers = {key.lower(): value for key, value in request.header_items()}
        body = json.loads(request.data)
        captured.append(
            {
                "url": request.full_url,
                "headers": headers,
                "body": body,
                "timeout": timeout,
            }
        )
        if body["method"] == "initialize":
            return _Response(
                {
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {"protocolVersion": MCP_PROTOCOL_VERSION},
                },
                headers={"Mcp-Session-Id": "transport-session"},
            )
        if body["method"] == "notifications/initialized":
            return _Response(text="")
        payload = {
            "results": [
                {
                    "title": "Free result",
                    "url": "https://example.com/free",
                    "excerpts": ["Free excerpt"],
                },
                {
                    "title": "Capped result",
                    "url": "https://example.com/capped",
                    "excerpts": ["Should be capped"],
                },
            ]
        }
        event = {
            "jsonrpc": "2.0",
            "id": body["id"],
            "result": {"structuredContent": payload},
        }
        messages = [
            {"jsonrpc": "2.0", "id": "other", "error": {"code": -32603}},
            {"jsonrpc": "2.0", "method": "notifications/message"},
            event,
            {"jsonrpc": "2.0", "id": "another", "result": {}},
        ]
        if encoding == "json":
            return _Response(messages)
        return _Response(
            text="".join(f"event: message\ndata: {json.dumps(m)}\n\n" for m in messages)
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("AGENT_WEB_SEARCH_PROVIDERS", "parallel")
    output = SearchEngine(timeout=9).search(SearchRequest("question", max_results=1))
    response = output.providers["parallel"]

    assert [call["body"]["method"] for call in captured] == [
        "initialize",
        "notifications/initialized",
        "tools/call",
    ]
    assert all(call["url"] == MCP_ENDPOINT for call in captured)
    assert all(call["headers"]["user-agent"] == USER_AGENT for call in captured)
    assert all("x-api-key" not in call["headers"] for call in captured)
    assert all(call["timeout"] == 9 for call in captured)
    assert captured[1]["headers"]["mcp-session-id"] == "transport-session"
    assert captured[2]["headers"]["mcp-protocol-version"] == MCP_PROTOCOL_VERSION
    arguments = captured[2]["body"]["params"]["arguments"]
    assert arguments["objective"] == "question"
    assert arguments["search_queries"] == ["question"]
    assert arguments["session_id"]
    assert response.error is None
    assert response.searched is True
    assert [item.url for item in response.results] == ["https://example.com/free"]
    assert output.to_dict()["providers"]["parallel"] == {
        "results": [
            {
                "title": "Free result",
                "url": "https://example.com/free",
                "description": "Free excerpt",
            }
        ]
    }


@pytest.mark.parametrize(
    ("stage", "reply"),
    [
        ("initialize", {"error": {"code": -32603, "message": "private detail"}}),
        ("initialize", {"result": None}),
        ("initialize", {"result": []}),
        ("initialize", {"result": {}}),
        ("initialize", {"result": {"protocolVersion": ""}}),
        ("initialize", {"result": {"protocolVersion": "  "}}),
        ("initialize", {"result": {"protocolVersion": 123}}),
        (
            "initialize",
            {"id": "other", "result": {"protocolVersion": MCP_PROTOCOL_VERSION}},
        ),
        ("tools/call", {"id": "other", "result": {"structuredContent": {}}}),
        ("tools/call", {"id": None, "result": {"structuredContent": {}}}),
        ("tools/call", {"error": {"code": -32603, "message": "private detail"}}),
        ("tools/call", {"result": {"isError": True, "content": []}}),
    ],
)
@pytest.mark.parametrize("encoding", ["json", "sse"])
def test_parallel_protocol_failure_reaches_engine(monkeypatch, stage, reply, encoding):
    calls = []

    def fake_urlopen(request, timeout=None):
        body = json.loads(request.data)
        calls.append(body["method"])
        if body["method"] == "notifications/initialized":
            return _Response(text="")
        result = {"result": {"protocolVersion": MCP_PROTOCOL_VERSION}}
        if body["method"] == stage:
            result = reply
        envelope = {"jsonrpc": "2.0", "id": body["id"], **result}
        if encoding == "json":
            return _Response(envelope)
        return _Response(text=f"data: {json.dumps(envelope)}\n\n")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("AGENT_WEB_SEARCH_PROVIDERS", "parallel")
    response = SearchEngine().search(SearchRequest("question"))

    assert response.all_providers_failed is True
    assert response.providers == {}
    assert response.failed_provider_errors == {
        "parallel": "parallel Free MCP RuntimeError"
    }
    payload, is_error = search_result_payload(response)
    assert is_error is True
    assert payload["error"]["code"] == "all_providers_failed"
    assert "private detail" not in json.dumps(payload)
    assert calls == (
        ["initialize"]
        if stage == "initialize"
        else ["initialize", "notifications/initialized", "tools/call"]
    )


@pytest.mark.parametrize("stage", ["initialize", "tools/call"])
@pytest.mark.parametrize(
    "failure",
    [TimeoutError("private detail"), urllib.error.URLError("private detail")],
)
def test_parallel_transport_failure_reaches_engine(monkeypatch, stage, failure):
    def fake_urlopen(request, timeout=None):
        body = json.loads(request.data)
        if body["method"] == stage:
            raise failure
        if body["method"] == "notifications/initialized":
            return _Response(text="")
        return _Response(
            {"id": body["id"], "result": {"protocolVersion": MCP_PROTOCOL_VERSION}}
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("AGENT_WEB_SEARCH_PROVIDERS", "parallel")
    response = SearchEngine().search(SearchRequest("question"))

    assert response.all_providers_failed is True
    assert response.failed_provider_errors == {
        "parallel": f"parallel Free MCP {type(failure).__name__}"
    }


def test_parallel_does_not_swallow_interrupt(monkeypatch):
    def interrupted_urlopen(request, timeout=None):
        raise KeyboardInterrupt

    monkeypatch.setattr(urllib.request, "urlopen", interrupted_urlopen)
    monkeypatch.setenv("AGENT_WEB_SEARCH_PROVIDERS", "parallel")
    with pytest.raises(KeyboardInterrupt):
        SearchEngine().search(SearchRequest("question"))


def test_parallel_maps_request_and_dense_excerpts(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return _Response(
            {
                "results": [
                    {
                        "title": "Parallel result",
                        "url": "https://example.com/parallel",
                        "publish_date": "2026-08-24",
                        "excerpts": ["First excerpt", "Second excerpt"],
                    },
                    {"title": "discarded without URL"},
                ]
            }
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    response = ParallelProvider(api_key="parallel-key", timeout=7).search(
        SearchRequest("latest infrastructure benchmarks", max_results=5)
    )

    assert captured["url"] == ENDPOINT
    assert captured["headers"]["X-api-key"] == "parallel-key"
    assert captured["payload"] == {
        "objective": "latest infrastructure benchmarks",
        "search_queries": ["latest infrastructure benchmarks"],
        "advanced_settings": {"max_results": 5},
    }
    assert captured["timeout"] == 7
    assert response.searched is True
    assert len(response.results) == 1
    assert response.results[0].description == "First excerpt\n\nSecond excerpt"
    assert response.results[0].published_at == "2026-08-24"
