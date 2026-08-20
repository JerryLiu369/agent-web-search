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
    engine = SearchEngine(
        providers={"ark": Fake("ark"), "gemini": Fake("gemini")}
    )
    assert list(engine.providers) == ["ark", "gemini"]


def test_optional_provider_can_be_selected_explicitly(monkeypatch):
    monkeypatch.delenv("AGENT_WEB_SEARCH_PROVIDERS", raising=False)
    engine = SearchEngine()
    result = engine.search(SearchRequest("hello", providers=["gemini"]))
    assert list(result.providers) == ["gemini"]
    assert result.providers["gemini"].error == "GEMINI_API_KEY is not set"
