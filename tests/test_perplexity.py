import json
import urllib.request

from agent_web_search.models import SearchRequest
from agent_web_search.providers.perplexity import ENDPOINT, PerplexityProvider


class _Response:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.data).encode()


def test_perplexity_requires_key():
    response = PerplexityProvider(api_key="").search(SearchRequest("question"))

    assert response.error == "PERPLEXITY_API_KEY is not set"
    assert response.searched is False


def test_perplexity_uses_native_search_api(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data)
        return _Response(
            {
                "results": [
                    {
                        "title": "Perplexity result",
                        "url": "https://example.com/perplexity",
                        "snippet": "Relevant snippet",
                        "date": "2026-08-23",
                        "last_updated": "2026-08-24",
                    }
                ]
            }
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    response = PerplexityProvider(api_key="pplx-key").search(
        SearchRequest("latest AI news", max_results=6, time_range="w")
    )

    assert captured["url"] == ENDPOINT
    assert captured["headers"]["Authorization"] == "Bearer pplx-key"
    assert captured["payload"] == {
        "query": "latest AI news",
        "max_results": 6,
        "search_recency_filter": "week",
    }
    assert response.searched is True
    assert response.answer == ""
    assert response.results[0].description == "Relevant snippet"
    assert response.results[0].published_at == "2026-08-23"
