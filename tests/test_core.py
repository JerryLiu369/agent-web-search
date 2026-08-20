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
