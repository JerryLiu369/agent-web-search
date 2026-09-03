from __future__ import annotations

import json
import urllib.error
from unittest.mock import patch

import pytest

from agent_web_search.models import SearchRequest
from agent_web_search.prompting import search_prompt
from agent_web_search.providers.zhipu_chat_search import (
    ZhipuChatSearchProvider,
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
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        code,
        "upstream body contains test-secret",
        hdrs={},  # type: ignore[arg-type]
        fp=None,
    )


def test_build_payload_uses_prompt_and_exact_native_search_controls():
    payload = build_payload("原始问题", "model-a", max_results=3, time_range="w")

    assert payload["model"] == "model-a"
    assert payload["stream"] is False
    assert payload["messages"] == [
        {
            "role": "user",
            "content": search_prompt("原始问题", time_range="w", max_results=3),
        }
    ]
    assert payload["tools"] == [
        {
            "type": "web_search",
            "web_search": {
                "enable": True,
                "search_engine": "search_pro",
                "search_result": True,
                "require_search": True,
                "result_sequence": "after",
                "search_query": "原始问题",
                "count": 3,
                "search_recency_filter": "oneWeek",
                "content_size": "medium",
            },
        }
    ]
    assert (
        "search_recency_filter"
        not in build_payload("q", "model")["tools"][0]["web_search"]
    )


def test_provider_is_registered_with_its_credential_env():
    spec = PROVIDER_SPECS["zhipu_chat_search"]

    assert spec.provider_type is ZhipuChatSearchProvider
    assert spec.credential_env == "ZHIPU_CHAT_SEARCH_API_KEY"


def test_parse_extracts_first_answer_and_deduplicated_top_level_results():
    response = parse(
        {
            "model": "server-model",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "answer with https://in-prose.test",
                    }
                },
                {"message": {"content": "ignore this later choice"}},
            ],
            "web_search": [
                {
                    "title": "A",
                    "link": "https://a.test",
                    "content": "content A",
                    "publish_date": "2026-09-03",
                },
                {"title": "duplicate", "link": "https://a.test"},
                {"title": "B", "link": "https://b.test"},
            ],
        },
        max_results=1,
    )

    assert response.provider == "zhipu_chat_search"
    assert response.model == "server-model"
    assert response.searched is True
    assert response.answer == "answer with https://in-prose.test"
    assert [
        (row.title, row.url, row.description, row.published_at)
        for row in response.results
    ] == [("A", "https://a.test", "content A", "2026-09-03")]


def test_parse_preserves_answer_with_empty_results_and_does_not_guess_from_answer():
    response = parse(
        {
            "choices": [{"message": {"content": "See https://example.test"}}],
            "web_search": [],
        }
    )

    assert response.searched is True
    assert response.answer == "See https://example.test"
    assert response.results == []


def test_parse_requires_a_top_level_web_search_array_for_searched():
    response = parse(
        {
            "choices": [{"message": {"content": "answer"}}],
            "message": {"web_search": [{"link": "https://not-top-level.test"}]},
        }
    )

    assert response.answer == "answer"
    assert response.results == []
    assert response.searched is False


def test_provider_uses_contract_default_model():
    provider = ZhipuChatSearchProvider(api_key="test-key")

    assert provider.models == ["glm-5.3-flash"]


def test_provider_reads_env_base_url_and_model_pool(monkeypatch):
    monkeypatch.setenv("ZHIPU_CHAT_SEARCH_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_WEB_SEARCH_ZHIPU_CHAT_BASE_URL", "https://gateway.test/")
    monkeypatch.setenv("AGENT_WEB_SEARCH_ZHIPU_CHAT_MODELS", "model-a,model-b\nmodel-a")

    provider = ZhipuChatSearchProvider()

    assert provider.endpoint == "https://gateway.test/api/paas/v4/chat/completions"
    assert provider.models == ["model-a", "model-b"]


def test_provider_round_robins_configured_models(monkeypatch):
    seen = []

    def fake_urlopen(request, **_kwargs):
        payload = json.loads(request.data)
        seen.append(payload["model"])
        return _Response(
            {
                "model": payload["model"],
                "choices": [{"message": {"content": "answer"}}],
                "web_search": [],
            }
        )

    monkeypatch.setattr(
        "agent_web_search.providers.zhipu_chat_search.urllib.request.urlopen",
        fake_urlopen,
    )
    provider = ZhipuChatSearchProvider(
        api_key="test-key",
        models=["model-a", "model-b"],
    )

    provider.search(SearchRequest("question"))
    provider.search(SearchRequest("question"))
    provider.search(SearchRequest("question"))

    assert seen == ["model-a", "model-b", "model-a"]


def test_provider_does_not_use_the_other_provider_key(monkeypatch):
    monkeypatch.setenv("ZHIPU_WEB_SEARCH_API_KEY", "web-key")

    response = ZhipuChatSearchProvider(models=["model"]).search(SearchRequest("q"))

    assert response.error == "ZHIPU_CHAT_SEARCH_API_KEY is not set"


def test_provider_posts_contract_payload_and_records_server_model():
    provider = ZhipuChatSearchProvider(
        api_key="test-key",
        base_url="https://gateway.test",
        models=["requested-model"],
    )
    body = {
        "model": "server-model",
        "choices": [{"message": {"content": "answer"}}],
        "web_search": [{"title": "A", "link": "https://a.test"}],
    }

    with patch(
        "agent_web_search.providers.zhipu_chat_search.urllib.request.urlopen",
        return_value=_Response(body),
    ) as opened:
        response = provider.search(
            SearchRequest("question", max_results=3, time_range="d")
        )

    request = opened.call_args.args[0]
    payload = json.loads(request.data)
    assert request.full_url == "https://gateway.test/api/paas/v4/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-key"
    assert payload["model"] == "requested-model"
    assert payload["stream"] is False
    assert payload["messages"][0]["content"].endswith("Question: question")
    assert payload["tools"][0]["type"] == "web_search"
    assert payload["tools"][0]["web_search"] == {
        "enable": True,
        "search_engine": "search_pro",
        "search_result": True,
        "require_search": True,
        "result_sequence": "after",
        "search_query": "question",
        "count": 3,
        "search_recency_filter": "oneDay",
        "content_size": "medium",
    }
    assert response.model == "server-model"
    assert response.searched is True


@pytest.mark.parametrize("status", [401, 429, 500, 502])
def test_provider_redacts_http_error_details(status):
    provider = ZhipuChatSearchProvider(api_key="test-secret", models=["model"])

    with patch(
        "agent_web_search.providers.zhipu_chat_search.urllib.request.urlopen",
        side_effect=_http_error(status),
    ):
        response = provider.search(SearchRequest("question"))

    assert response.error == f"Zhipu Chat Search HTTP {status}"
    assert response.error is not None
    assert "test-secret" not in response.error
    assert "upstream body" not in response.error


def test_provider_reports_timeout_network_error_and_generic_error_without_details():
    provider = ZhipuChatSearchProvider(api_key="test-secret", models=["model"])

    with patch(
        "agent_web_search.providers.zhipu_chat_search.urllib.request.urlopen",
        side_effect=TimeoutError("test-secret timeout detail"),
    ):
        timeout = provider.search(SearchRequest("question"))

    with patch(
        "agent_web_search.providers.zhipu_chat_search.urllib.request.urlopen",
        side_effect=urllib.error.URLError("test-secret network detail"),
    ):
        network = provider.search(SearchRequest("question"))

    with patch(
        "agent_web_search.providers.zhipu_chat_search.urllib.request.urlopen",
        side_effect=RuntimeError("test-secret generic detail"),
    ):
        generic = provider.search(SearchRequest("question"))

    assert timeout.error == "Zhipu Chat Search request timed out"
    assert network.error == "Zhipu Chat Search network error"
    assert generic.error == "Zhipu Chat Search request error"
    for response in (timeout, network, generic):
        assert response.error is not None
        assert "test-secret" not in response.error


def test_provider_reports_invalid_json_and_non_object_response():
    provider = ZhipuChatSearchProvider(api_key="test-key", models=["model"])

    with patch(
        "agent_web_search.providers.zhipu_chat_search.urllib.request.urlopen",
        return_value=_Response(b"not-json"),
    ):
        invalid = provider.search(SearchRequest("question"))

    with patch(
        "agent_web_search.providers.zhipu_chat_search.urllib.request.urlopen",
        return_value=_Response(["not", "an", "object"]),
    ):
        non_object = provider.search(SearchRequest("question"))

    assert invalid.error == "Zhipu Chat Search returned invalid JSON"
    assert non_object.error == "Zhipu Chat Search response JSON must be an object"
