from __future__ import annotations

import json
from unittest.mock import patch

from agent_web_search.models import SearchRequest
from agent_web_search.providers.codex_alpha import (
    CodexAlphaProvider,
    build_payload,
    parse_results,
)


def test_payload_is_normal_web_search_only():
    payload = build_payload("q", "model")
    assert payload["commands"] == {"search_query": [{"q": "q"}]}
    assert payload["settings"] == {
        "external_web_access": True,
        "search_context_size": "low",
    }
    assert not {"input", "response_length", "allowed_callers"}.intersection(payload)


def test_parse_text_results_ignores_unknown_items():
    response = parse_results(
        {
            "output": "summary",
            "results": [
                {
                    "type": "text_result",
                    "title": "A",
                    "url": "https://a.test/",
                    "description": "desc",
                },
                {"type": "text_result", "url": "https://a.test/"},
                {"type": "media_result", "media_url": "https://cdn.test/a.jpg"},
                {"type": "unknown", "ref_id": "opaque"},
            ],
        },
        max_results=1,
    )
    assert response.answer == "summary"
    assert len(response.results) == 1
    assert response.results[0].url == "https://a.test/"


def test_provider_requires_server_side_credentials():
    response = CodexAlphaProvider(api_key="", endpoint="https://gateway.test").search(
        SearchRequest("q")
    )
    assert response.error == "AGENT_WEB_SEARCH_CODEX_ALPHA_API_KEY is not set"


def test_provider_posts_complete_endpoint_without_modifying_path():
    provider = CodexAlphaProvider(
        api_key="secret", endpoint="https://gateway.test/custom/alpha", model="m"
    )
    body = {"model": "m", "results": [{"title": "T", "url": "https://a.test"}]}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(body).encode()

    with patch(
        "agent_web_search.providers.codex_alpha.urllib.request.urlopen",
        return_value=_Response(),
    ) as opened:
        response = provider.search(SearchRequest("q"))
    request = opened.call_args.args[0]
    assert request.full_url == "https://gateway.test/custom/alpha"
    assert response.results[0].url == "https://a.test"
