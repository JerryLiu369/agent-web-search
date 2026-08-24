import json

from agent_web_search.model_pool import RoundRobinModels
from agent_web_search.models import SearchRequest
from agent_web_search.providers.ark import ArkProvider
from agent_web_search.providers.gemini import GeminiProvider
from agent_web_search.providers.grok import GrokProvider


class _Response:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.data).encode()


def test_round_robin_uses_one_or_many_models_deterministically():
    single = RoundRobinModels(["only"])
    multiple = RoundRobinModels(["first", "second"])

    assert [single.next(), single.next()] == ["only", "only"]
    assert [multiple.next(), multiple.next(), multiple.next()] == [
        "first",
        "second",
        "first",
    ]


def test_plural_model_env_accepts_commas_newlines_and_duplicates(monkeypatch):
    monkeypatch.setenv(
        "AGENT_WEB_SEARCH_GEMINI_MODELS", "gemini-a,gemini-b\ngemini-a"
    )

    provider = GeminiProvider(api_key="test-key")

    assert provider.models == ["gemini-a", "gemini-b"]


def test_ark_round_robins_models_between_requests(monkeypatch):
    seen = []

    def fake_urlopen(request, timeout=None):
        payload = json.loads(request.data)
        seen.append(payload["model"])
        return _Response(
            {
                "model": payload["model"],
                "output": [
                    {"type": "web_search_call", "status": "completed"},
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": "complete " * 20}
                        ],
                    },
                ],
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = ArkProvider(api_key="test-key", models=["ark-a", "ark-b"])

    provider.search(SearchRequest("question"))
    provider.search(SearchRequest("question"))
    provider.search(SearchRequest("question"))

    assert seen == ["ark-a", "ark-b", "ark-a"]


def test_gemini_and_grok_round_robin_models_between_requests(monkeypatch):
    seen = []

    def fake_urlopen(request, timeout=None):
        payload = json.loads(request.data)
        seen.append(payload["model"])
        return _Response({"model": payload["model"], "output": []})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    gemini = GeminiProvider(api_key="test-key", models=["gemini-a", "gemini-b"])
    grok = GrokProvider(api_key="test-key", models=["grok-a", "grok-b"])

    for provider in (gemini, grok):
        provider.search(SearchRequest("question"))
        provider.search(SearchRequest("question"))
        provider.search(SearchRequest("question"))

    assert seen == [
        "gemini-a",
        "gemini-b",
        "gemini-a",
        "grok-a",
        "grok-b",
        "grok-a",
    ]
