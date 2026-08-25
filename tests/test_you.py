import json
import urllib.request

from agent_web_search.models import SearchRequest
from agent_web_search.providers.you import ENDPOINT, YouProvider


class _Response:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.data).encode()


def test_you_requires_key():
    response = YouProvider(api_key="").search(SearchRequest("question"))

    assert response.error == "YDC_API_KEY is not set"
    assert response.searched is False


def test_you_maps_web_and_news_results_and_deduplicates(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data)
        return _Response(
            {
                "results": {
                    "web": [
                        {
                            "title": "Web result",
                            "url": "https://example.com/web",
                            "description": "Fallback description",
                            "snippets": ["First snippet", "Second snippet"],
                            "page_age": "2026-08-24T08:15:00",
                        }
                    ],
                    "news": [
                        {
                            "title": "Duplicate",
                            "url": "https://example.com/web",
                            "snippets": ["Duplicate snippet"],
                        },
                        {
                            "title": "News result",
                            "url": "https://example.com/news",
                            "description": "News description",
                        },
                    ],
                }
            }
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    response = YouProvider(api_key="you-key").search(
        SearchRequest("latest world news", max_results=2, time_range="d")
    )

    assert captured["url"] == ENDPOINT
    assert captured["headers"]["X-api-key"] == "you-key"
    assert captured["payload"] == {
        "query": "latest world news",
        "count": 2,
        "freshness": "day",
    }
    assert response.searched is True
    assert [item.url for item in response.results] == [
        "https://example.com/web",
        "https://example.com/news",
    ]
    assert response.results[0].description == "First snippet\n\nSecond snippet"
    assert response.results[1].description == "News description"
