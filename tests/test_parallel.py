import json
import urllib.request

from agent_web_search.models import SearchRequest
from agent_web_search.providers.parallel import ENDPOINT, ParallelProvider


class _Response:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.data).encode()


def test_parallel_requires_key():
    response = ParallelProvider(api_key="").search(SearchRequest("question"))

    assert response.error == "PARALLEL_API_KEY is not set"
    assert response.searched is False


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
