import json

from agent_web_search.models import ProviderResponse, SearchRequest, SearchResult
from agent_web_search.providers.ark import ArkProvider


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(
            {
                "id": "resp-1",
                "model": "m",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "short",
                                "annotations": [
                                    {"type": "url_citation", "url": "https://initial"}
                                ],
                            }
                        ],
                    },
                    {"type": "web_search_call", "status": "completed"},
                ],
            }
        ).encode()


def test_ark_continuation_merges_initial_and_followup_citations(monkeypatch):
    provider = ArkProvider(api_key="test-key", models=["m"])
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: _Response())
    monkeypatch.setattr(
        provider,
        "_continue",
        lambda *_args: ProviderResponse(
            provider="ark",
            answer="A complete answer",
            citations=[
                SearchResult(title="follow-up", url="https://followup", provider="ark")
            ],
            searched=True,
        ),
    )

    result = provider.search(SearchRequest("question"))

    assert result.searched is True
    assert result.answer == "A complete answer"
    assert [item.url for item in result.citations] == [
        "https://initial",
        "https://followup",
    ]
