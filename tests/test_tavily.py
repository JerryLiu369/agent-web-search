import json

from agent_web_search.models import SearchRequest
from agent_web_search.providers.tavily import TavilyProvider
from agent_web_search.schema import build_tool_schema


class _Response:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.data).encode()


def test_tavily_adapts_common_controls(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return _Response(
            {
                "results": [
                    {
                        "title": "Example",
                        "url": "https://example.com",
                        "content": "Result summary",
                    }
                ]
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    response = TavilyProvider(api_key="test-key", timeout=12).search(
        SearchRequest(
            query="latest AI news",
            max_results=7,
            max_keyword=2,
            time_range="w",
        )
    )

    assert captured["payload"]["max_results"] == 7
    assert captured["payload"]["time_range"] == "week"
    assert "max_keyword" not in captured["payload"]
    assert captured["timeout"] == 12
    assert response.searched is True
    assert response.results[0].url == "https://example.com"


def test_tavily_success_is_searched_even_without_results(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *_args, **_kwargs: _Response({"results": []}),
    )
    response = TavilyProvider(api_key="test-key").search(SearchRequest("empty"))
    assert response.searched is True
    assert response.results == []


def test_tavily_only_appears_when_startup_enabled():
    default_schema = build_tool_schema(["ark", "ddgs", "exa"])
    tavily_schema = build_tool_schema(["ark", "tavily"])
    default_items = default_schema["parameters"]["properties"]["providers"]["items"]
    tavily_items = tavily_schema["parameters"]["properties"]["providers"]["items"]
    assert "tavily" not in default_items["enum"]
    assert "tavily" in tavily_items["enum"]
    assert "Tavily web search" in tavily_schema["description"]
