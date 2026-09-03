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
        "https://api.deepseek.com/responses",
        code,
        "error",
        hdrs={},  # type: ignore[arg-type]
        fp=None,
    )


def test_build_payload_forces_deepseek_web_search():
    payload = build_payload("search prompt", "deepseek-test")

    assert payload == {
        "model": "deepseek-test",
        "input": "search prompt",
        "tools": [{"type": "web_search"}],
        "tool_choice": {"type": "web_search"},
        "max_output_tokens": 4096,
    }


def test_provider_is_registered_with_its_credential_env():
    spec = PROVIDER_SPECS["deepseek"]

    assert spec.provider_type is DeepSeekProvider
    assert spec.credential_env == "DEEPSEEK_API_KEY"


def test_parse_extracts_answer_and_deduplicated_citations_with_limit():
    response = parse(
        {
            "model": "deepseek-test",
            "output": [
                {
                    "type": "reasoning",
                    "content": [{"type": "reasoning_text", "text": "ignore"}],
                },
                {"type": "web_search_call", "status": "completed"},
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "first answer",
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "url": "https://a.test",
                                    "title": "A",
                                },
                                {
                                    "type": "url_citation",
                                    "url": "https://a.test",
                                    "title": "duplicate",
                                },
                            ],
                        },
                        {
                            "type": "text",
                            "text": "second answer",
                            "annotations": [
                                {"type": "url_citation", "url": "https://b.test"},
                                {"type": "url_citation", "url": ""},
                                {"type": "other", "url": "https://ignored.test"},
                            ],
                        },
                    ],
                },
            ],
        },
        max_results=1,
    )

    assert response.provider == "deepseek"
    assert response.model == "deepseek-test"
    assert response.searched is True
    assert response.answer == "second answer"
    assert [(row.title, row.url, row.description) for row in response.results] == [
        ("A", "https://a.test", "")
    ]


def test_parse_uses_top_level_output_text_without_citations():
    response = parse(
        {
            "model": "deepseek-test",
            "output": [{"type": "web_search_call", "status": "completed"}],
            "output_text": "answer without mapped citations",
        }
    )

    assert response.searched is True
    assert response.answer == "answer without mapped citations"
    assert response.results == []


def test_parse_handles_empty_and_malformed_output():
    assert parse({"output": None}).results == []
    assert (
        parse({"output": [{"type": "message", "content": "not-a-list"}, "bad"]}).results
        == []
    )
    assert parse({"output": {"type": "message"}}).answer == ""


def test_provider_reads_env_base_url_and_models(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_WEB_SEARCH_DEEPSEEK_BASE_URL", "https://gateway.test/v1/")
    monkeypatch.setenv("AGENT_WEB_SEARCH_DEEPSEEK_MODELS", "model-a,model-b\nmodel-a")

    provider = DeepSeekProvider()

    assert provider.endpoint == "https://gateway.test/v1/responses"
    assert provider.models == ["model-a", "model-b"]


def test_provider_requires_server_side_credentials():
    response = DeepSeekProvider(api_key="", models=["model"]).search(SearchRequest("q"))

    assert response.error == "DEEPSEEK_API_KEY is not set"


def test_provider_posts_to_responses_and_parses_response():
    provider = DeepSeekProvider(
        api_key="test-key",
        base_url="https://gateway.test/v1",
        models=["model"],
    )
    body = {
        "model": "model",
        "output": [
            {"type": "web_search_call", "status": "completed"},
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "answer",
                        "annotations": [
                            {
                                "type": "url_citation",
                                "url": "https://a.test",
                                "title": "A",
                            }
                        ],
                    }
                ],
            },
        ],
    }

    with patch(
        "agent_web_search.providers.deepseek.urllib.request.urlopen",
        return_value=_Response(body),
    ) as opened:
        response = provider.search(SearchRequest("question", max_results=3))

    request = opened.call_args.args[0]
    payload = json.loads(request.data)
    assert request.full_url == "https://gateway.test/v1/responses"
    assert request.headers["Authorization"] == "Bearer test-key"
    assert payload["tools"] == [{"type": "web_search"}]
    assert payload["tool_choice"] == {"type": "web_search"}
    assert "question" in payload["input"]
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
