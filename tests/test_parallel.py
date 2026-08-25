import json
import urllib.request

from agent_web_search.models import SearchRequest
from agent_web_search.providers.parallel import (
    ENDPOINT,
    MCP_ENDPOINT,
    MCP_PROTOCOL_VERSION,
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


def test_parallel_without_key_uses_free_mcp(monkeypatch):
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
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
        return _Response(text=f"event: message\ndata: {json.dumps(event)}\n\n")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    response = ParallelProvider(api_key="", timeout=9).search(
        SearchRequest("question", max_results=1)
    )

    assert [call["body"]["method"] for call in captured] == [
        "initialize",
        "notifications/initialized",
        "tools/call",
    ]
    assert all(call["url"] == MCP_ENDPOINT for call in captured)
    assert all("x-api-key" not in call["headers"] for call in captured)
    assert captured[1]["headers"]["mcp-session-id"] == "transport-session"
    assert captured[2]["headers"]["mcp-protocol-version"] == MCP_PROTOCOL_VERSION
    arguments = captured[2]["body"]["params"]["arguments"]
    assert arguments["objective"] == "question"
    assert arguments["search_queries"] == ["question"]
    assert arguments["session_id"]
    assert response.error is None
    assert response.searched is True
    assert [item.url for item in response.results] == ["https://example.com/free"]


def test_parallel_maps_request_and_dense_excerpts(monkeypatch):
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
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
