from __future__ import annotations

import json
import urllib.error
from unittest.mock import patch

import pytest

from agent_web_search.models import SearchRequest
from agent_web_search.providers.zhipu_web_search import (
    ZhipuWebSearchProvider,
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
        "https://open.bigmodel.cn/api/paas/v4/web_search",
        code,
        "upstream body contains test-secret",
        hdrs={},  # type: ignore[arg-type]
        fp=None,
    )


def test_build_payload_maps_common_controls_and_fixed_web_search_options():
    assert build_payload("原始问题", max_results=3, time_range="w") == {
        "search_engine": "search_pro",
        "search_intent": False,
        "count": 3,
        "search_query": "原始问题",
        "search_recency_filter": "oneWeek",
        "content_size": "medium",
    }
    assert "search_recency_filter" not in build_payload("q")


def test_provider_is_registered_with_its_credential_env():
    spec = PROVIDER_SPECS["zhipu_web_search"]

    assert spec.provider_type is ZhipuWebSearchProvider
    assert spec.credential_env == "ZHIPU_WEB_SEARCH_API_KEY"


def test_parse_maps_deduplicates_valid_urls_and_truncates_locally():
    response = parse(
        {
            "search_result": [
                {
                    "title": "A",
                    "link": "https://a.test",
                    "content": "content A",
                    "publish_date": "2026-09-03",
                },
                {"title": "bad", "link": "not-a-url"},
                {"title": "duplicate", "link": "https://a.test"},
                {"title": "B", "link": "https://b.test", "content": "content B"},
            ]
        },
        max_results=1,
    )

    assert response.provider == "zhipu_web_search"
    assert response.searched is True
    assert [
        (row.title, row.url, row.description, row.published_at)
        for row in response.results
    ] == [("A", "https://a.test", "content A", "2026-09-03")]


def test_parse_without_a_search_result_array_is_not_marked_searched():
    response = parse({"answer": "not part of this API"})

    assert response.searched is False
    assert response.results == []


def test_provider_reads_env_base_url(monkeypatch):
    monkeypatch.setenv("ZHIPU_WEB_SEARCH_API_KEY", "test-key")
    monkeypatch.setenv(
        "AGENT_WEB_SEARCH_ZHIPU_WEB_SEARCH_BASE_URL", "https://gateway.test/"
    )

    provider = ZhipuWebSearchProvider()

    assert provider.endpoint == "https://gateway.test/api/paas/v4/web_search"


def test_provider_requires_its_own_server_side_credential():
    response = ZhipuWebSearchProvider(api_key="").search(SearchRequest("q"))

    assert response.error == "ZHIPU_WEB_SEARCH_API_KEY is not set"


def test_provider_posts_contract_payload_and_parses_response():
    provider = ZhipuWebSearchProvider(
        api_key="test-key",
        base_url="https://gateway.test",
    )
    body = {
        "search_result": [
            {
                "title": "A",
                "link": "https://a.test",
                "content": "snippet",
            }
        ]
    }

    with patch(
        "agent_web_search.providers.zhipu_web_search.urllib.request.urlopen",
        return_value=_Response(body),
    ) as opened:
        response = provider.search(
            SearchRequest("question", max_results=3, time_range="d")
        )

    request = opened.call_args.args[0]
    payload = json.loads(request.data)
    assert request.full_url == "https://gateway.test/api/paas/v4/web_search"
    assert request.headers["Authorization"] == "Bearer test-key"
    assert payload == {
        "search_engine": "search_pro",
        "search_intent": False,
        "count": 3,
        "search_query": "question",
        "search_recency_filter": "oneDay",
        "content_size": "medium",
    }
    assert response.searched is True
    assert response.results[0].url == "https://a.test"


@pytest.mark.parametrize("status", [401, 429, 500, 502])
def test_provider_redacts_http_error_details(status):
    provider = ZhipuWebSearchProvider(api_key="test-secret")

    with patch(
        "agent_web_search.providers.zhipu_web_search.urllib.request.urlopen",
        side_effect=_http_error(status),
    ):
        response = provider.search(SearchRequest("question"))

    assert response.error == f"Zhipu Web Search HTTP {status}"
    assert response.error is not None
    assert "test-secret" not in response.error
    assert "upstream body" not in response.error


def test_provider_reports_timeout_network_error_and_generic_error_without_details():
    provider = ZhipuWebSearchProvider(api_key="test-secret")

    with patch(
        "agent_web_search.providers.zhipu_web_search.urllib.request.urlopen",
        side_effect=TimeoutError("test-secret timeout detail"),
    ):
        timeout = provider.search(SearchRequest("question"))

    with patch(
        "agent_web_search.providers.zhipu_web_search.urllib.request.urlopen",
        side_effect=urllib.error.URLError("test-secret network detail"),
    ):
        network = provider.search(SearchRequest("question"))

    with patch(
        "agent_web_search.providers.zhipu_web_search.urllib.request.urlopen",
        side_effect=RuntimeError("test-secret generic detail"),
    ):
        generic = provider.search(SearchRequest("question"))

    assert timeout.error == "Zhipu Web Search request timed out"
    assert network.error == "Zhipu Web Search network error"
    assert generic.error == "Zhipu Web Search request error"
    for response in (timeout, network, generic):
        assert response.error is not None
        assert "test-secret" not in response.error


def test_provider_reports_invalid_json_and_non_object_response():
    provider = ZhipuWebSearchProvider(api_key="test-key")

    with patch(
        "agent_web_search.providers.zhipu_web_search.urllib.request.urlopen",
        return_value=_Response(b"not-json"),
    ):
        invalid = provider.search(SearchRequest("question"))

    with patch(
        "agent_web_search.providers.zhipu_web_search.urllib.request.urlopen",
        return_value=_Response(["not", "an", "object"]),
    ):
        non_object = provider.search(SearchRequest("question"))

    assert invalid.error == "Zhipu Web Search returned invalid JSON"
    assert non_object.error == "Zhipu Web Search response JSON must be an object"
