import pytest

from agent_web_search.engine import SearchEngine
from agent_web_search.models import (
    ProviderResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)


class Fake:
    def __init__(self, name):
        self.name = name

    def search(self, request):
        return ProviderResponse(
            provider=self.name,
            results=[
                SearchResult(
                    title=self.name, url=f"https://{self.name}.test", provider=self.name
                )
            ],
            searched=True,
        )


class Failing:
    def __init__(self, name, error="provider failed"):
        self.name = name
        self.error = error

    def search(self, request):
        return ProviderResponse(provider=self.name, error=self.error)


def test_engine_runs_selected_providers():
    out = SearchEngine(providers={"a": Fake("a"), "b": Fake("b")}).search(
        SearchRequest("hello", providers=["a"])
    )
    assert list(out.providers) == ["a"]
    assert out.providers["a"].results[0].url == "https://a.test"


def test_engine_omits_failed_providers_from_successful_results():
    out = SearchEngine(
        providers={"ok": Fake("ok"), "failed": Failing("failed", "boom")}
    ).search(SearchRequest("hello"))

    assert list(out.providers) == ["ok"]
    assert out.failed_provider_errors == {"failed": "boom"}
    assert out.all_providers_failed is False


def test_engine_tracks_failures_when_every_provider_fails():
    out = SearchEngine(
        providers={
            "first": Failing("first", "first error"),
            "second": Failing("second", "second error"),
        }
    ).search(SearchRequest("hello"))

    assert out.providers == {}
    assert out.failed_provider_errors == {
        "first": "first error",
        "second": "second error",
    }
    assert out.all_providers_failed is True


def test_empty_query_rejected():
    with pytest.raises(ValueError, match="empty") as exc_info:
        SearchEngine(providers={}).search(SearchRequest("  "))
    assert "empty" in str(exc_info.value)


def test_default_provider_set_requires_no_api_keys(monkeypatch):
    monkeypatch.delenv("AGENT_WEB_SEARCH_PROVIDERS", raising=False)
    engine = SearchEngine()
    assert engine.enabled_provider_names == ["ddgs", "exa", "parallel"]


def test_public_provider_response_only_contains_answer_and_results():
    response = SearchResponse(
        query="hello",
        providers={
            "model": ProviderResponse(
                provider="model",
                answer="answer",
                results=[SearchResult(url="https://example.com")],
                model="model-id",
                searched=True,
            )
        },
    )

    provider = response.to_dict()["providers"]["model"]

    assert provider == {
        "answer": "answer",
        "results": [
            {
                "title": "",
                "url": "https://example.com",
                "description": "",
                "provider": "",
            }
        ],
    }


def test_disabled_provider_cannot_be_selected_at_request_time(monkeypatch):
    monkeypatch.setenv("AGENT_WEB_SEARCH_PROVIDERS", "ddgs,exa")
    engine = SearchEngine()
    result = engine.search(SearchRequest("hello", providers=["gemini"]))
    assert list(result.providers) == []


def test_common_controls_are_normalized_before_provider_dispatch():
    class Capture(Fake):
        def search(self, request):
            self.request = request
            return super().search(request)

    provider = Capture("capture")
    SearchEngine(providers={"capture": provider}).search(
        SearchRequest(
            "  hello  ",
            max_results=100,
            max_keyword=0,
            time_range="invalid",
            providers=["capture", "capture"],
        )
    )
    assert provider.request.query == "hello"
    assert provider.request.max_results == 20
    assert provider.request.max_keyword == 1
    assert provider.request.time_range is None
    assert provider.request.providers == ["capture"]


def test_disabled_provider_bad_configuration_does_not_block_startup(monkeypatch):
    monkeypatch.setenv("AGENT_WEB_SEARCH_PROVIDERS", "ddgs,exa,parallel")
    monkeypatch.setenv("AGENT_WEB_SEARCH_ARK_MODELS", ",")

    engine = SearchEngine()

    assert engine.enabled_provider_names == ["ddgs", "exa", "parallel"]
    assert not hasattr(engine, "_all_providers")


def test_enabled_provider_bad_configuration_has_a_readable_error(monkeypatch):
    monkeypatch.setenv("AGENT_WEB_SEARCH_PROVIDERS", "ark")
    monkeypatch.setenv("AGENT_WEB_SEARCH_ARK_MODELS", " , ")

    with pytest.raises(
        ValueError, match="must contain at least one model"
    ) as exc_info:
        SearchEngine()
    assert (
        str(exc_info.value)
        == "AGENT_WEB_SEARCH_ARK_MODELS must contain at least one model"
    )


@pytest.mark.parametrize("raw_timeout", ["abc", "0", "-1", "inf", "nan"])
def test_invalid_timeout_has_a_readable_error(monkeypatch, raw_timeout):
    monkeypatch.setenv("AGENT_WEB_SEARCH_TIMEOUT", raw_timeout)

    with pytest.raises(
        ValueError, match="must be a positive number"
    ) as exc_info:
        SearchEngine()
    assert (
        str(exc_info.value)
        == "AGENT_WEB_SEARCH_TIMEOUT must be a positive number"
    )


def test_positive_timeout_is_accepted(monkeypatch):
    monkeypatch.setenv("AGENT_WEB_SEARCH_TIMEOUT", "0.5")
    engine = SearchEngine(providers={})
    assert engine.enabled_provider_names == []
