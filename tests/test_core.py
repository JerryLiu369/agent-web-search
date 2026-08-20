from agent_web_search.engine import SearchEngine
from agent_web_search.models import ProviderResponse, SearchRequest, SearchResult


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


def test_engine_runs_selected_providers():
    out = SearchEngine(providers={"a": Fake("a"), "b": Fake("b")}).search(
        SearchRequest("hello", providers=["a"])
    )
    assert list(out.providers) == ["a"]
    assert out.providers["a"].results[0].url == "https://a.test"


def test_empty_query_rejected():
    try:
        SearchEngine(providers={}).search(SearchRequest("  "))
    except ValueError as exc:
        assert "empty" in str(exc)
    else:
        assert False


def test_optional_provider_selection_is_not_enabled_by_default(monkeypatch):
    monkeypatch.delenv("AGENT_WEB_SEARCH_PROVIDERS", raising=False)
    engine = SearchEngine(providers={"ark": Fake("ark"), "gemini": Fake("gemini")})
    assert list(engine.providers) == ["ark", "gemini"]


def test_disabled_provider_cannot_be_selected_at_request_time(monkeypatch):
    monkeypatch.setenv("AGENT_WEB_SEARCH_PROVIDERS", "ark,ddgs,exa")
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
