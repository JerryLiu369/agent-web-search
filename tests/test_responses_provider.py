from __future__ import annotations

import json
import urllib.error
from unittest.mock import patch

import pytest

from agent_web_search.models import SearchRequest
from agent_web_search.providers.responses import (
    ResponsesProvider,
    build_payload,
    parse,
)
from agent_web_search.registry import PROVIDER_SPECS


class _Response:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        if isinstance(self.data, bytes):
            return self.data
        return json.dumps(self.data).encode()


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://gateway.test/v1/responses",
        code,
        "error",
        hdrs={},  # type: ignore[arg-type]
        fp=None,
    )


def _standard_body() -> dict:
    return {
        "id": "resp_123",
        "object": "response",
        "status": "completed",
        "model": "gpt-5-mini",
        "output": [
            {"id": "rs_01", "type": "reasoning", "summary": "..."},
            {
                "id": "ws_01",
                "type": "web_search_call",
                "status": "completed",
                "action": {
                    "type": "search",
                    "query": "2026 US Open winner",
                    "sources": [
                        {
                            "type": "url",
                            "url": "https://www.usopen.org/news/a",
                            "title": "US Open Official",
                        },
                        {
                            "type": "url",
                            "url": "https://www.usopen.org/news/a",
                            "title": "duplicate",
                        },
                        {"type": "url", "url": "", "title": "empty"},
                    ],
                },
            },
            {
                "id": "msg_01",
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Alexander Zverev won the 2026 US Open.",
                        "annotations": [
                            {
                                "type": "url_citation",
                                "url": "https://www.usopen.org/news/b",
                                "title": "usopen.org",
                                "start_index": 0,
                                "end_index": 20,
                            }
                        ],
                    }
                ],
            },
        ],
    }


def test_provider_is_registered_with_its_credential_env():
    spec = PROVIDER_SPECS["responses"]

    assert spec.provider_type is ResponsesProvider
    assert spec.credential_env == "AGENT_WEB_SEARCH_RESPONSES_API_KEY"


def test_build_payload_uses_configured_tool_type():
    payload = build_payload("search prompt", "model-a", "web_search")

    assert payload == {
        "model": "model-a",
        "input": "search prompt",
        "tools": [{"type": "web_search"}],
    }


def test_parse_standard_response_with_reasoning_first():
    response = parse(_standard_body(), max_results=10)

    assert response.provider == "responses"
    assert response.model == "gpt-5-mini"
    assert response.searched is True
    assert response.answer == "Alexander Zverev won the 2026 US Open."
    assert [(row.title, row.url) for row in response.results] == [
        ("US Open Official", "https://www.usopen.org/news/a"),
        ("usopen.org", "https://www.usopen.org/news/b"),
    ]


def test_parse_applies_max_results_limit():
    response = parse(_standard_body(), max_results=1)

    assert len(response.results) == 1
    assert response.results[0].url == "https://www.usopen.org/news/a"


def test_parse_annotations_only_without_sources():
    response = parse(
        {
            "model": "model-a",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "answer with citation",
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "url": "https://example.test/cited",
                                    "title": "Cited",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    )

    assert response.searched is True
    assert response.answer == "answer with citation"
    assert [(row.title, row.url) for row in response.results] == [
        ("Cited", "https://example.test/cited")
    ]


def test_parse_message_without_urls_marks_not_searched():
    response = parse(
        {
            "model": "model-a",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "direct answer"}],
                }
            ],
        }
    )

    assert response.answer == "direct answer"
    assert response.results == []
    assert response.searched is False


def test_parse_matches_custom_tool_type():
    response = parse(
        {
            "output": [
                {
                    "type": "custom_search_call",
                    "action": {
                        "sources": [{"url": "https://custom.test", "title": "Custom"}]
                    },
                }
            ]
        },
        tool_type="custom_search",
    )

    assert response.searched is True
    assert response.results[0].url == "https://custom.test"


def test_parse_handles_malformed_output():
    assert parse({"output": None}).results == []
    assert parse({"output": "bad"}).results == []
    assert parse({"output": [{"type": "message", "content": "bad"}]}).results == []
    assert parse({}).searched is False


def test_provider_reads_env_base_url_models_and_tool_type(monkeypatch):
    monkeypatch.setenv(
        "AGENT_WEB_SEARCH_RESPONSES_BASE_URL", "https://gateway.test/v1/"
    )
    monkeypatch.delenv("AGENT_WEB_SEARCH_RESPONSES_ENDPOINT", raising=False)
    monkeypatch.setenv("AGENT_WEB_SEARCH_RESPONSES_API_KEY", "env-key")
    monkeypatch.setenv("AGENT_WEB_SEARCH_RESPONSES_MODELS", "model-a,model-b\nmodel-a")
    monkeypatch.setenv("AGENT_WEB_SEARCH_RESPONSES_TOOL_TYPE", "custom_search")

    provider = ResponsesProvider()

    assert provider.endpoint == "https://gateway.test/v1/responses"
    assert provider.models == ["model-a", "model-b"]
    assert provider.tool_type == "custom_search"


def test_provider_base_url_appends_v1_responses_when_needed():
    assert (
        ResponsesProvider(api_key="k", base_url="https://api.openai.com").endpoint
        == "https://api.openai.com/v1/responses"
    )
    assert (
        ResponsesProvider(api_key="k", base_url="https://api.openai.com/v1").endpoint
        == "https://api.openai.com/v1/responses"
    )
    assert (
        ResponsesProvider(
            api_key="k", base_url="https://api.openai.com/v1/responses"
        ).endpoint
        == "https://api.openai.com/v1/responses"
    )


def test_provider_defaults_to_openai_base_url_and_model(monkeypatch):
    monkeypatch.delenv("AGENT_WEB_SEARCH_RESPONSES_BASE_URL", raising=False)
    monkeypatch.delenv("AGENT_WEB_SEARCH_RESPONSES_ENDPOINT", raising=False)
    monkeypatch.delenv("AGENT_WEB_SEARCH_RESPONSES_MODELS", raising=False)

    provider = ResponsesProvider(api_key="k")

    assert provider.endpoint == "https://api.openai.com/v1/responses"
    assert provider.models == ["gpt-5-mini"]


def test_provider_supports_legacy_endpoint_env(monkeypatch):
    monkeypatch.delenv("AGENT_WEB_SEARCH_RESPONSES_BASE_URL", raising=False)
    monkeypatch.setenv("AGENT_WEB_SEARCH_RESPONSES_ENDPOINT", "https://legacy.test/v1/")

    assert ResponsesProvider(api_key="k").endpoint == "https://legacy.test/v1/responses"


def test_provider_falls_back_to_openai_key(monkeypatch):
    monkeypatch.delenv("AGENT_WEB_SEARCH_RESPONSES_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")

    assert ResponsesProvider(models=["m"]).api_key == "openai-key"

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert ResponsesProvider(models=["m"]).api_key == ""


def test_explicit_empty_api_key_does_not_fall_back_to_environment(monkeypatch):
    monkeypatch.setenv("AGENT_WEB_SEARCH_RESPONSES_API_KEY", "env-key")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")

    assert ResponsesProvider(api_key="", models=["m"]).api_key == ""


def test_provider_requires_base_url_and_credentials():
    missing_key = ResponsesProvider(
        api_key="", base_url="https://gateway.test/v1", models=["m"]
    )
    assert (
        missing_key.search(SearchRequest("q")).error
        == "AGENT_WEB_SEARCH_RESPONSES_API_KEY is not set"
    )

    missing_base_url = ResponsesProvider(api_key="key", base_url="", models=["m"])
    assert (
        missing_base_url.search(SearchRequest("q")).error
        == "AGENT_WEB_SEARCH_RESPONSES_BASE_URL is not set"
    )


def test_provider_posts_responses_payload_and_parses_response():
    provider = ResponsesProvider(
        api_key="test-key",
        base_url="https://gateway.test/v1",
        models=["model-a"],
    )

    with patch(
        "agent_web_search.providers.responses.urllib.request.urlopen",
        return_value=_Response(_standard_body()),
    ) as opened:
        response = provider.search(SearchRequest("question", max_results=5))

    request = opened.call_args.args[0]
    payload = json.loads(request.data)
    assert request.full_url == "https://gateway.test/v1/responses"
    assert request.headers["Authorization"] == "Bearer test-key"
    assert payload["model"] == "model-a"
    assert payload["tools"] == [{"type": "web_search"}]
    assert payload["input"].startswith("Search")
    assert response.answer == "Alexander Zverev won the 2026 US Open."
    assert response.results[0].url == "https://www.usopen.org/news/a"
    assert response.model == "gpt-5-mini"


def test_provider_rotates_models_round_robin():
    provider = ResponsesProvider(
        api_key="key",
        base_url="https://gateway.test/v1",
        models=["model-a", "model-b"],
    )
    seen = []
    with patch(
        "agent_web_search.providers.responses.urllib.request.urlopen",
        side_effect=[
            _Response({"output": [], "model": "model-a"}),
            _Response({"output": [], "model": "model-b"}),
        ],
    ) as opened:
        provider.search(SearchRequest("q"))
        seen.append(json.loads(opened.call_args.args[0].data)["model"])
        provider.search(SearchRequest("q"))
        seen.append(json.loads(opened.call_args.args[0].data)["model"])

    assert seen == ["model-a", "model-b"]


@pytest.mark.parametrize("status", [401, 429, 500, 502])
def test_provider_maps_http_errors_without_leaking_key(status):
    provider = ResponsesProvider(
        api_key="test-secret",
        base_url="https://gateway.test/v1",
        models=["m"],
    )

    with patch(
        "agent_web_search.providers.responses.urllib.request.urlopen",
        side_effect=_http_error(status),
    ):
        response = provider.search(SearchRequest("question"))

    assert response.error == f"responses HTTP {status}"
    assert "test-secret" not in response.error


def test_provider_reports_invalid_json_and_non_object_response():
    provider = ResponsesProvider(
        api_key="test-key",
        base_url="https://gateway.test/v1",
        models=["m"],
    )

    with patch(
        "agent_web_search.providers.responses.urllib.request.urlopen",
        return_value=_Response(b"not-json"),
    ):
        invalid = provider.search(SearchRequest("question"))

    with patch(
        "agent_web_search.providers.responses.urllib.request.urlopen",
        return_value=_Response(["not", "an", "object"]),
    ):
        non_object = provider.search(SearchRequest("question"))

    assert "test-key" not in (invalid.error or "")
    assert "test-key" not in (non_object.error or "")
    assert non_object.error == "responses response JSON must be an object"
