import json
import urllib.request
from urllib.parse import parse_qs, urlparse

from agent_web_search.models import SearchRequest
from agent_web_search.providers.brave import BraveProvider


class _FakeResponse:
    def __init__(self, body: dict):
        self._body = json.dumps(body).encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_brave_requires_key():
    response = BraveProvider(api_key="").search(SearchRequest(query="kernel papers"))
    assert response.searched is False
    assert response.error == "BRAVE_SEARCH_API_KEY is not set"


def test_brave_search_maps_controls_and_normalizes_results(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["timeout"] = timeout
        return _FakeResponse(
            {
                "web": {
                    "results": [
                        {
                            "title": "Kernel paper",
                            "url": "https://example.com/kernel",
                            "description": "A result snippet",
                            "age": "2 days ago",
                        },
                        {"title": "Discarded without URL"},
                    ]
                }
            }
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    response = BraveProvider(api_key="brave-test-key", timeout=7).search(
        SearchRequest(query="GPU kernel papers", max_results=5, time_range="w")
    )

    assert response.error is None
    assert response.searched is True
    assert len(response.results) == 1
    result = response.results[0]
    assert result.title == "Kernel paper"
    assert result.url == "https://example.com/kernel"
    assert result.description == "A result snippet"
    assert result.provider == "brave"

    query = parse_qs(urlparse(captured["url"]).query)
    assert urlparse(captured["url"]).scheme == "https"
    assert urlparse(captured["url"]).netloc == "api.search.brave.com"
    assert urlparse(captured["url"]).path == "/res/v1/web/search"
    assert query == {"q": ["GPU kernel papers"], "count": ["5"], "freshness": ["pw"]}
    assert captured["headers"].get("X-subscription-token") == "brave-test-key"
    assert captured["headers"].get("Accept") == "application/json"
    assert captured["timeout"] == 7
