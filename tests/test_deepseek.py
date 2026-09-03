from __future__ import annotations

import json
import urllib.error
from unittest.mock import patch

import pytest

from agent_web_search.models import SearchRequest
from agent_web_search.providers.deepseek import (
    DeepSeekProvider,
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
        "https://api.deepseek.com/anthropic/v1/messages",
        code,
        "error",
        hdrs={},  # type: ignore[arg-type]
        fp=None,
    )


def test_build_payload_uses_anthropic_web_search_tool():
    payload = build_payload("search prompt", "deepseek-test")

    assert payload == {
        "model": "deepseek-test",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": "search prompt"}],
        "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
    }


def test_provider_is_registered_with_its_credential_env():
    spec = PROVIDER_SPECS["deepseek"]

    assert spec.provider_type is DeepSeekProvider
    assert spec.credential_env == "DEEPSEEK_API_KEY"


def test_parse_extracts_answer_and_deduplicated_search_results_with_limit():
    response = parse(
        {
            "model": "deepseek-test",
            "content": [
                {"type": "thinking", "thinking": "ignore"},
                {
                    "type": "server_tool_use",
                    "name": "web_search",
                    "input": {"query": "question"},
                },
                {
                    "type": "web_search_tool_result",
                    "tool_use_id": "tool-1",
                    "content": [
                        {
                            "type": "web_search_result",
                            "title": "A",
                            "url": "https://a.test",
                            "page_age": "2026-09-03",
                        },
                        {
                            "type": "web_search_result",
                            "title": "duplicate",
                            "url": "https://a.test",
                        },
                        {"type": "web_search_result", "url": "https://b.test"},
                    ],
                },
                {
                    "type": "text",
                    "text": "final answer",
                },
            ],
        },
        max_results=1,
    )

    assert response.provider == "deepseek"
    assert response.model == "deepseek-test"
    assert response.searched is True
    assert response.answer == "final answer"
    assert [(row.title, row.url, row.description) for row in response.results] == [
        ("A", "https://a.test", "")
    ]
    assert response.results[0].published_at is None
    assert response.results[0].author is None


def test_parse_preserves_answer_without_search_results():
    response = parse(
        {
            "model": "deepseek-test",
            "content": [
                {"type": "server_tool_use", "name": "web_search"},
                {"type": "web_search_tool_result", "content": []},
                {"type": "text", "text": "answer without results"},
            ],
        }
    )

    assert response.searched is True
    assert response.answer == "answer without results"
    assert response.results == []


def test_parse_does_not_turn_plain_answer_urls_into_results():
    response = parse(
        {"content": [{"type": "text", "text": "See https://example.test"}]}
    )

    assert response.answer == "See https://example.test"
    assert response.results == []


def test_parse_handles_empty_and_malformed_content():
    assert parse({"content": None}).results == []
    assert parse({"content": [{"type": "text", "text": ""}, "bad"]}).results == []
    assert (
        parse(
            {"content": [{"type": "web_search_tool_result", "content": "bad"}]}
        ).results
        == []
    )
    assert (
        parse({"content": [{"type": "web_search_result", "url": "https://a.test"}]})
        .results[0]
        .url
        == "https://a.test"
    )


def test_provider_reads_env_base_url_and_models(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv(
        "AGENT_WEB_SEARCH_DEEPSEEK_BASE_URL", "https://gateway.test/anthropic/"
    )
    monkeypatch.setenv("AGENT_WEB_SEARCH_DEEPSEEK_MODELS", "model-a,model-b\nmodel-a")

    provider = DeepSeekProvider()

    assert provider.endpoint == "https://gateway.test/anthropic/v1/messages"
    assert provider.models == ["model-a", "model-b"]


def test_provider_requires_server_side_credentials():
    response = DeepSeekProvider(api_key="", models=["model"]).search(SearchRequest("q"))

    assert response.error == "DEEPSEEK_API_KEY is not set"


def test_provider_posts_anthropic_messages_and_parses_response():
    provider = DeepSeekProvider(
        api_key="test-key",
        base_url="https://gateway.test/anthropic",
        models=["model"],
    )
    body = {
        "model": "model",
        "content": [
            {"type": "server_tool_use", "name": "web_search"},
            {
                "type": "web_search_tool_result",
                "content": [
                    {
                        "type": "web_search_result",
                        "title": "A",
                        "url": "https://a.test",
                    }
                ],
            },
            {"type": "text", "text": "answer"},
        ],
    }

    with patch(
        "agent_web_search.providers.deepseek.urllib.request.urlopen",
        return_value=_Response(body),
    ) as opened:
        response = provider.search(SearchRequest("question", max_results=3))

    request = opened.call_args.args[0]
    payload = json.loads(request.data)
    assert request.full_url == "https://gateway.test/anthropic/v1/messages"
    assert request.headers["X-api-key"] == "test-key"
    assert request.headers["Anthropic-version"] == "2023-06-01"
    assert payload["messages"][0]["content"].startswith("Search")
    assert payload["tools"] == [
        {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}
    ]
    assert response.answer == "answer"
    assert response.results[0].url == "https://a.test"


@pytest.mark.parametrize("status", [401, 429, 500, 502])
def test_provider_redacts_http_error_details(status):
    provider = DeepSeekProvider(api_key="test-secret", models=["model"])

    with patch(
        "agent_web_search.providers.deepseek.urllib.request.urlopen",
        side_effect=_http_error(status),
    ):
        response = provider.search(SearchRequest("question"))

    assert response.error == f"DeepSeek HTTP {status}"
    assert response.error is not None
    assert "test-secret" not in response.error


def test_provider_reports_timeout_without_exception_details():
    provider = DeepSeekProvider(api_key="test-secret", models=["model"])

    with patch(
        "agent_web_search.providers.deepseek.urllib.request.urlopen",
        side_effect=TimeoutError("test-secret timeout detail"),
    ):
        response = provider.search(SearchRequest("question"))

    assert response.error == "DeepSeek request timed out"
    assert response.error is not None
    assert "test-secret" not in response.error


def test_provider_reports_invalid_json_and_non_object_response():
    provider = DeepSeekProvider(api_key="test-key", models=["model"])

    with patch(
        "agent_web_search.providers.deepseek.urllib.request.urlopen",
        return_value=_Response(b"not-json"),
    ):
        invalid = provider.search(SearchRequest("question"))

    with patch(
        "agent_web_search.providers.deepseek.urllib.request.urlopen",
        return_value=_Response(["not", "an", "object"]),
    ):
        non_object = provider.search(SearchRequest("question"))

    assert invalid.error == "DeepSeek returned invalid JSON"
    assert non_object.error == "DeepSeek response JSON must be an object"
