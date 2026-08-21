import json
import urllib.request

from agent_web_search.models import SearchRequest
from agent_web_search.providers.exa import ExaProvider


def test_exa_parser_preserves_multiline_highlights():
    text = """Title: Example
URL: https://example.com
Published: 2026-08-20
Author: Example Author
Highlights:
First line
Second line

---

Title: Other
URL: https://other.example
Highlights: Inline summary
"""
    results = ExaProvider.parse_text(text)
    assert len(results) == 2
    assert results[0].description == "First line Second line"
    assert results[0].published_at == "2026-08-20"
    assert results[1].description == "Inline summary"


class _FakeResponse:
    def __init__(self, body: dict):
        self._body = json.dumps(body).encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_exa_api_path_uses_key_and_parses_results(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["payload"] = json.loads(req.data.decode())
        return _FakeResponse(
            {
                "results": [
                    {
                        "title": "Paper",
                        "url": "https://example.com/paper",
                        "publishedDate": "2026-08-01",
                        "author": "Alice",
                        "highlights": ["highlight one", "highlight two"],
                    },
                    {"title": "No URL entry"},
                ]
            }
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    provider = ExaProvider(api_key="test-key", timeout=5)
    resp = provider.search(
        SearchRequest(query="kernel papers", max_results=5, time_range="m")
    )

    assert resp.error is None
    assert resp.searched is True
    assert len(resp.results) == 1
    assert resp.results[0].url == "https://example.com/paper"
    assert resp.results[0].description == "highlight one highlight two"
    assert resp.results[0].published_at == "2026-08-01"
    assert resp.results[0].author == "Alice"

    assert captured["url"] == "https://api.exa.ai/search"
    assert captured["headers"].get("X-api-key") == "test-key"
    assert captured["payload"]["numResults"] == 5
    assert "startPublishedDate" in captured["payload"]


def test_exa_mcp_path_used_without_key(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["has_key"] = any(
            k.lower() == "x-api-key" for k, _ in req.header_items()
        )
        body = (
            'data: {"result": {"content": [{"type": "text", '
            '"text": "Title: T\\nURL: https://x.example\\nHighlights: h"}]}}\n'
        )
        return _FakeResponse({}) if False else _RawResponse(body)

    class _RawResponse:
        def __init__(self, text):
            self._text = text

        def read(self):
            return self._text.encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    provider = ExaProvider(api_key="", timeout=5)
    resp = provider.search(SearchRequest(query="q", max_results=3))

    assert captured["url"] == "https://mcp.exa.ai/mcp"
    assert captured["has_key"] is False
    assert resp.error is None
    assert len(resp.results) == 1
    assert resp.results[0].url == "https://x.example"
