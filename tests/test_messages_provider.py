from __future__ import annotations

import json
import urllib.error
from unittest.mock import patch

import pytest

from agent_web_search.models import SearchRequest
from agent_web_search.providers.messages import (
    MessagesProvider,
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
        "https://api.anthropic.com/v1/messages",
        code,
        "error",
        hdrs={},  # type: ignore[arg-type]
        fp=None,
    )


def _standard_body() -> dict:
    return {
        "id": "msg_123",
        "model": "claude-3-7-sonnet-20250219",
        "content": [
            {"type": "thinking", "thinking": "plan the search"},
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
                        "url": "https://a.test/page",
                        "description": "description A",
                    },
                    {
                        "type": "web_search_result",
                        "title": "duplicate",
                        "url": "https://a.test/page",
                        "description": "ignored",
                    },
                    {
                        "type": "web_search_result",
                        "title": "",
                        "url": "https://b.test/page",
                        "snippet": "snippet B",
                    },
                    {"type": "web_search_result", "url": ""},
                    {"type": "other", "url": "https://ignored.test"},
                ],
            },
            {"type": "text", "text": "final answer"},
        ],
    }


def test_provider_is_registered_with_its_credential_env():
    spec = PROVIDER_SPECS["messages"]

    assert spec.provider_type is MessagesProvider
    assert spec.credential_env == "AGENT_WEB_SEARCH_MESSAGES_API_KEY"


def test_build_payload_uses_configurable_tool():
    payload = build_payload("search prompt", "model-a")

    assert payload == {
        "model": "model-a",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": "search prompt"}],
        "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
    }

    custom = build_payload("search prompt", "model-a", "custom_tool", "custom_name")

    assert custom["tools"] == [
        {"type": "custom_tool", "name": "custom_name", "max_uses": 5}
    ]


def test_parse_extracts_answer_and_deduplicated_search_results_with_limit():
    response = parse(_standard_body(), max_results=2)

    assert response.provider == "messages"
    assert response.model == "claude-3-7-sonnet-20250219"
    assert response.searched is True
    assert response.answer == "final answer"
    assert [(row.title, row.url, row.description) for row in response.results] == [
        ("A", "https://a.test/page", "description A"),
        ("b.test", "https://b.test/page", "snippet B"),
    ]


def test_parse_supports_top_level_web_search_result_blocks():
    response = parse(
        {
            "content": [
                {
                    "type": "web_search_result",
                    "title": "Direct",
                    "url": "https://direct.test",
                    "description": "direct hit",
                }
            ]
        }
    )

    assert response.searched is True
    assert [(row.title, row.url) for row in response.results] == [
        ("Direct", "https://direct.test")
    ]


def test_parse_collects_multiple_text_blocks_and_tool_use_marks_searched():
    response = parse(
        {
            "content": [
                {"type": "text", "text": "part one"},
                {"type": "tool_use", "name": "web_search"},
                {"type": "text", "text": "part two"},
            ]
        }
    )

    assert response.answer == "part one\n\npart two"
    assert response.results == []
    assert response.searched is True


def test_parse_preserves_answer_without_search_results():
    response = parse(
        {
            "model": "model-a",
            "content": [{"type": "text", "text": "answer without results"}],
        }
    )

    assert response.searched is False
    assert response.answer == "answer without results"
    assert response.results == []


def test_parse_backfills_title_from_citations_and_domain():
    response = parse(
        {
            "content": [
                {
                    "type": "web_search_tool_result",
                    "content": [
                        {"type": "web_search_result", "url": "https://x.test/p"}
                    ],
                },
                {
                    "type": "text",
                    "text": "answer",
                    "citations": [
                        {"type": "web", "url": "https://x.test/p", "title": "Cited"}
                    ],
                },
            ]
        }
    )

    assert response.searched is True
    assert response.answer == "answer"
    assert [(row.title, row.url) for row in response.results] == [
        ("Cited", "https://x.test/p")
    ]


def test_parse_handles_empty_and_malformed_content():
    assert parse({"content": None}).results == []
    assert parse({"content": [{"type": "text", "text": ""}, "bad"]}).results == []
    assert parse({"content": "bad"}).results == []
    assert (
        parse(
            {"content": [{"type": "web_search_tool_result", "content": "bad"}]}
        ).searched
        is True
    )
    assert parse({}).searched is False
    assert parse({"content": [{"type": "text", "text": 123}]}).answer == ""


def test_provider_reads_env_base_url_models_tool_and_timeout(monkeypatch):
    monkeypatch.setenv("AGENT_WEB_SEARCH_MESSAGES_API_KEY", "env-key")
    monkeypatch.setenv(
        "AGENT_WEB_SEARCH_MESSAGES_BASE_URL", "https://gateway.test/anthropic/"
    )
    monkeypatch.delenv("AGENT_WEB_SEARCH_MESSAGES_ENDPOINT", raising=False)
    monkeypatch.setenv("AGENT_WEB_SEARCH_MESSAGES_MODELS", "model-a,model-b\nmodel-a")
    monkeypatch.setenv("AGENT_WEB_SEARCH_MESSAGES_TOOL_TYPE", "custom_type")
    monkeypatch.setenv("AGENT_WEB_SEARCH_MESSAGES_TOOL_NAME", "custom_name")
    monkeypatch.setenv("AGENT_WEB_SEARCH_MESSAGES_TIMEOUT", "7")

    provider = MessagesProvider()

    assert provider.api_key == "env-key"
    assert provider.endpoint == "https://gateway.test/anthropic/v1/messages"
    assert provider.models == ["model-a", "model-b"]
    assert provider.tool_type == "custom_type"
    assert provider.tool_name == "custom_name"
    assert provider.timeout == 7


def test_provider_endpoint_normalization_and_endpoint_override():
    assert (
        MessagesProvider(api_key="k", base_url="https://api.anthropic.com").endpoint
        == "https://api.anthropic.com/v1/messages"
    )
    assert (
        MessagesProvider(
            api_key="k", base_url="https://api.anthropic.com/v1/messages"
        ).endpoint
        == "https://api.anthropic.com/v1/messages"
    )
    assert (
        MessagesProvider(
            api_key="k",
            base_url="https://ignored.test",
            endpoint="https://custom.test/full",
        ).endpoint
        == "https://custom.test/full"
    )


def test_provider_defaults_to_anthropic_models_and_timeout(monkeypatch):
    monkeypatch.delenv("AGENT_WEB_SEARCH_MESSAGES_BASE_URL", raising=False)
    monkeypatch.delenv("AGENT_WEB_SEARCH_MESSAGES_ENDPOINT", raising=False)
    monkeypatch.delenv("AGENT_WEB_SEARCH_MESSAGES_MODELS", raising=False)
    monkeypatch.delenv("AGENT_WEB_SEARCH_MESSAGES_TIMEOUT", raising=False)

    provider = MessagesProvider(api_key="k")

    assert provider.endpoint == "https://api.anthropic.com/v1/messages"
    assert provider.models == [
        "claude-3-7-sonnet-20250219",
        "claude-3-5-haiku-20241022",
    ]
    assert provider.tool_type == "web_search_20250305"
    assert provider.tool_name == "web_search"
    assert provider.timeout == 60.0


def test_provider_endpoint_env_takes_priority_over_base_url(monkeypatch):
    monkeypatch.setenv(
        "AGENT_WEB_SEARCH_MESSAGES_BASE_URL", "https://base.test/anthropic"
    )
    monkeypatch.setenv("AGENT_WEB_SEARCH_MESSAGES_ENDPOINT", "https://ep.test/full")

    assert MessagesProvider(api_key="k").endpoint == "https://ep.test/full"


def test_provider_requires_credentials_and_endpoint():
    missing_key = MessagesProvider(api_key="", models=["m"])

    assert (
        missing_key.search(SearchRequest("q")).error
        == "AGENT_WEB_SEARCH_MESSAGES_API_KEY is not set"
    )

    missing_endpoint = MessagesProvider(api_key="k", endpoint="", models=["m"])

    assert (
        missing_endpoint.search(SearchRequest("q")).error
        == "AGENT_WEB_SEARCH_MESSAGES_BASE_URL is not set"
    )


def test_provider_posts_messages_payload_and_parses_response():
    provider = MessagesProvider(
        api_key="test-key",
        base_url="https://gateway.test/anthropic",
        models=["model-a"],
    )
    body = {
        "model": "model-a",
        "content": [
            {"type": "server_tool_use", "name": "web_search"},
            {
                "type": "web_search_tool_result",
                "content": [
                    {
                        "type": "web_search_result",
                        "title": "A",
                        "url": "https://a.test",
                        "description": "desc",
                    }
                ],
            },
            {"type": "text", "text": "answer"},
        ],
    }

    with patch(
        "agent_web_search.providers.messages.urllib.request.urlopen",
        return_value=_Response(body),
    ) as opened:
        response = provider.search(SearchRequest("question", max_results=3))

    request = opened.call_args.args[0]
    payload = json.loads(request.data)
    assert request.full_url == "https://gateway.test/anthropic/v1/messages"
    assert request.headers["X-api-key"] == "test-key"
    assert request.headers["Anthropic-version"] == "2023-06-01"
    assert payload["model"] == "model-a"
    assert payload["max_tokens"] == 4096
    assert payload["messages"][0]["content"].startswith("Search")
    assert payload["tools"] == [
        {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}
    ]
    assert response.answer == "answer"
    assert response.results[0].url == "https://a.test"
    assert response.model == "model-a"


def test_provider_rotates_models_round_robin():
    provider = MessagesProvider(
        api_key="key",
        base_url="https://gateway.test/anthropic",
        models=["model-a", "model-b"],
    )
    seen = []
    with patch(
        "agent_web_search.providers.messages.urllib.request.urlopen",
        side_effect=[
            _Response({"content": [], "model": "model-a"}),
            _Response({"content": [], "model": "model-b"}),
        ],
    ) as opened:
        provider.search(SearchRequest("q"))
        seen.append(json.loads(opened.call_args.args[0].data)["model"])
        provider.search(SearchRequest("q"))
        seen.append(json.loads(opened.call_args.args[0].data)["model"])

    assert seen == ["model-a", "model-b"]


@pytest.mark.parametrize("status", [401, 429, 500, 502])
def test_provider_maps_http_errors_without_leaking_key(status):
    provider = MessagesProvider(
        api_key="test-secret",
        base_url="https://gateway.test/anthropic",
        models=["m"],
    )

    with patch(
        "agent_web_search.providers.messages.urllib.request.urlopen",
        side_effect=_http_error(status),
    ):
        response = provider.search(SearchRequest("question"))

    assert response.error == f"messages HTTP {status}"
    assert "test-secret" not in response.error


def test_provider_maps_network_exceptions_without_leaking_key():
    provider = MessagesProvider(
        api_key="test-secret",
        base_url="https://gateway.test/anthropic",
        models=["m"],
    )

    with patch(
        "agent_web_search.providers.messages.urllib.request.urlopen",
        side_effect=urllib.error.URLError("test-secret detail"),
    ):
        response = provider.search(SearchRequest("question"))

    assert response.error == "messages URLError"
    assert "test-secret" not in response.error


def test_provider_reports_invalid_json_and_non_object_response():
    provider = MessagesProvider(
        api_key="test-key",
        base_url="https://gateway.test/anthropic",
        models=["m"],
    )

    with patch(
        "agent_web_search.providers.messages.urllib.request.urlopen",
        return_value=_Response(b"not-json"),
    ):
        invalid = provider.search(SearchRequest("question"))

    with patch(
        "agent_web_search.providers.messages.urllib.request.urlopen",
        return_value=_Response(["not", "an", "object"]),
    ):
        non_object = provider.search(SearchRequest("question"))

    assert "test-key" not in (invalid.error or "")
    assert "test-key" not in (non_object.error or "")
    assert non_object.error == "messages response JSON must be an object"


def test_explicit_empty_api_key_does_not_fall_back_to_environment(monkeypatch):
    monkeypatch.setenv("AGENT_WEB_SEARCH_MESSAGES_API_KEY", "environment-secret")

    provider = MessagesProvider(api_key="", models=["m"])

    assert provider.api_key == ""
