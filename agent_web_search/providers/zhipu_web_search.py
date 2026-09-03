from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from ..models import ProviderResponse, SearchRequest
from .base import Provider
from .zhipu_common import map_search_results, recency_filter, result_limit

DEFAULT_BASE_URL = "https://open.bigmodel.cn"
API_KEY_ENV = "ZHIPU_WEB_SEARCH_API_KEY"
BASE_URL_ENV = "AGENT_WEB_SEARCH_ZHIPU_WEB_SEARCH_BASE_URL"
ENDPOINT_PATH = "/api/paas/v4/web_search"


def _endpoint(base_url: str) -> str:
    return f"{base_url.rstrip('/')}{ENDPOINT_PATH}"


def build_payload(
    query: str,
    max_results: int = 10,
    time_range: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "search_engine": "search_pro",
        "search_intent": False,
        "count": result_limit(max_results),
        "search_query": query,
        "content_size": "medium",
    }
    recency = recency_filter(time_range)
    if recency is not None:
        payload["search_recency_filter"] = recency
    return payload


def parse(data: dict[str, Any], max_results: int = 10) -> ProviderResponse:
    if "error" in data:
        return ProviderResponse(
            provider="zhipu_web_search",
            error="Zhipu Web Search upstream error",
        )
    rows = data.get("search_result")
    if not isinstance(rows, list):
        return ProviderResponse(
            provider="zhipu_web_search",
            error="Zhipu Web Search response missing search_result",
        )
    return ProviderResponse(
        provider="zhipu_web_search",
        results=map_search_results(rows, "zhipu_web_search", max_results),
        searched=True,
    )


class ZhipuWebSearchProvider(Provider):
    """Zhipu's standalone China Web Search API."""

    name = "zhipu_web_search"
    parse = staticmethod(parse)

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60,
    ):
        self.api_key = api_key if api_key is not None else os.getenv(API_KEY_ENV, "")
        configured_base_url = (
            base_url
            if base_url is not None
            else os.getenv(BASE_URL_ENV, DEFAULT_BASE_URL)
        )
        self.endpoint = _endpoint(configured_base_url)
        self.timeout = timeout

    def search(self, request: SearchRequest) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(
                provider=self.name,
                error=f"{API_KEY_ENV} is not set",
            )
        payload = build_payload(
            request.query,
            max_results=request.max_results,
            time_range=request.time_range,
        )
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode(),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode(errors="replace"))
            if not isinstance(data, dict):
                return ProviderResponse(
                    provider=self.name,
                    error="Zhipu Web Search response JSON must be an object",
                )
            return self.parse(data, max_results=request.max_results)
        except urllib.error.HTTPError as exc:
            return ProviderResponse(
                provider=self.name,
                error=f"Zhipu Web Search HTTP {exc.code}",
            )
        except json.JSONDecodeError:
            return ProviderResponse(
                provider=self.name,
                error="Zhipu Web Search returned invalid JSON",
            )
        except TimeoutError:
            return ProviderResponse(
                provider=self.name,
                error="Zhipu Web Search request timed out",
            )
        except urllib.error.URLError:
            return ProviderResponse(
                provider=self.name,
                error="Zhipu Web Search network error",
            )
        except Exception:  # noqa: BLE001 - provider/network errors vary
            return ProviderResponse(
                provider=self.name,
                error="Zhipu Web Search request error",
            )
