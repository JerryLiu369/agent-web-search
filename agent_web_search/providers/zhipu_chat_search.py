from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from ..model_pool import RoundRobinModels, configured_models
from ..models import ProviderResponse, SearchRequest
from ..prompting import search_prompt
from .base import Provider
from .zhipu_common import map_search_results, recency_filter, result_limit, text

DEFAULT_BASE_URL = "https://open.bigmodel.cn"
DEFAULT_MODEL = "glm-5.3-flash"
API_KEY_ENV = "ZHIPU_CHAT_SEARCH_API_KEY"
BASE_URL_ENV = "AGENT_WEB_SEARCH_ZHIPU_CHAT_BASE_URL"
MODEL_ENV = "AGENT_WEB_SEARCH_ZHIPU_CHAT_MODELS"
ENDPOINT_PATH = "/api/paas/v4/chat/completions"


def _endpoint(base_url: str) -> str:
    return f"{base_url.rstrip('/')}{ENDPOINT_PATH}"


def build_payload(
    query: str,
    model: str,
    max_results: int = 10,
    time_range: str | None = None,
) -> dict[str, Any]:
    web_search: dict[str, Any] = {
        "enable": True,
        "search_engine": "search_pro",
        "search_result": True,
        "require_search": True,
        "result_sequence": "after",
        "search_query": query,
        "count": result_limit(max_results),
        "content_size": "medium",
    }
    recency = recency_filter(time_range)
    if recency is not None:
        web_search["search_recency_filter"] = recency
    return {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": search_prompt(
                    query,
                    time_range=time_range,
                    max_results=max_results,
                ),
            }
        ],
        "tools": [{"type": "web_search", "web_search": web_search}],
        "stream": False,
    }


def parse(data: dict[str, Any], max_results: int = 10) -> ProviderResponse:
    if "error" in data:
        return ProviderResponse(
            provider="zhipu_chat_search",
            error="Zhipu Chat Search upstream error",
        )
    answer = ""
    choices = data.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        message = choices[0].get("message")
        if isinstance(message, dict):
            answer = text(message.get("content"))
    rows = data.get("web_search")
    return ProviderResponse(
        provider="zhipu_chat_search",
        answer=answer,
        results=map_search_results(
            rows if isinstance(rows, list) else [], "zhipu_chat_search", max_results
        ),
        model=text(data.get("model")),
        searched=isinstance(rows, list),
    )


class ZhipuChatSearchProvider(Provider):
    """Zhipu Chat Completions with native web search."""

    name = "zhipu_chat_search"
    parse = staticmethod(parse)

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        models: list[str] | None = None,
        timeout: float = 60,
    ):
        self.api_key = api_key if api_key is not None else os.getenv(API_KEY_ENV, "")
        configured_base_url = (
            base_url
            if base_url is not None
            else os.getenv(BASE_URL_ENV, DEFAULT_BASE_URL)
        )
        self.endpoint = _endpoint(configured_base_url)
        self.models = configured_models(
            models=models,
            env_name=MODEL_ENV,
            defaults=[DEFAULT_MODEL],
        )
        self._model_pool = RoundRobinModels(self.models)
        self.timeout = timeout

    def search(self, request: SearchRequest) -> ProviderResponse:
        model = self._model_pool.next()
        if not self.api_key:
            return ProviderResponse(
                provider=self.name,
                model=model,
                error=f"{API_KEY_ENV} is not set",
            )
        payload = build_payload(
            request.query,
            model,
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
                    model=model,
                    error="Zhipu Chat Search response JSON must be an object",
                )
            parsed = self.parse(data, max_results=request.max_results)
            parsed.model = text(data.get("model")) or model
            return parsed
        except urllib.error.HTTPError as exc:
            return ProviderResponse(
                provider=self.name,
                model=model,
                error=f"Zhipu Chat Search HTTP {exc.code}",
            )
        except json.JSONDecodeError:
            return ProviderResponse(
                provider=self.name,
                model=model,
                error="Zhipu Chat Search returned invalid JSON",
            )
        except TimeoutError:
            return ProviderResponse(
                provider=self.name,
                model=model,
                error="Zhipu Chat Search request timed out",
            )
        except urllib.error.URLError:
            return ProviderResponse(
                provider=self.name,
                model=model,
                error="Zhipu Chat Search network error",
            )
        except Exception:  # noqa: BLE001 - provider/network errors vary
            return ProviderResponse(
                provider=self.name,
                model=model,
                error="Zhipu Chat Search request error",
            )
