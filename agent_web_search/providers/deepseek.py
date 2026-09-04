from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from ..model_pool import RoundRobinModels, configured_models
from ..models import ProviderResponse, SearchRequest, SearchResult
from ..prompting import search_prompt
from .base import Provider

DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com/anthropic"
API_KEY_ENV = "DEEPSEEK_API_KEY"
BASE_URL_ENV = "AGENT_WEB_SEARCH_DEEPSEEK_BASE_URL"
MODEL_ENV = "AGENT_WEB_SEARCH_DEEPSEEK_MODELS"
TOOL_TYPE = "web_search_20250305"
TOOL_NAME = "web_search"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _endpoint(base_url: str) -> str:
    base = base_url.rstrip("/")
    return base if base.endswith("/v1/messages") else f"{base}/v1/messages"


def _content_blocks(block: dict[str, Any]) -> list[dict[str, Any]]:
    content = block.get("content")
    if isinstance(content, list):
        return [item for item in content if isinstance(item, dict)]
    if isinstance(content, dict):
        return [content]
    return []


def build_payload(prompt: str, model: str) -> dict[str, Any]:
    return {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
        "tools": [{"type": TOOL_TYPE, "name": TOOL_NAME, "max_uses": 5}],
    }


def parse(data: dict[str, Any], max_results: int = 10) -> ProviderResponse:
    """Parse an Anthropic Messages response from DeepSeek."""
    try:
        limit = max(1, int(max_results))
    except (OverflowError, TypeError, ValueError):
        limit = 10

    answer = ""
    results: list[SearchResult] = []
    seen_urls: set[str] = set()
    searched = False
    content = data.get("content") if isinstance(data, dict) else []
    if not isinstance(content, list):
        content = []

    for block in content:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        searched |= block_type in {"server_tool_use", "web_search_tool_result"}
        if block_type == "text":
            text = _text(block.get("text"))
            if text:
                answer = text
        result_blocks = (
            _content_blocks(block) if block_type == "web_search_tool_result" else []
        )
        if block_type == "web_search_result":
            result_blocks.append(block)
        for result in result_blocks:
            if result.get("type") != "web_search_result":
                continue
            url = _text(result.get("url"))
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            results.append(
                SearchResult(
                    title=_text(result.get("title")),
                    url=url,
                    description=_text(
                        result.get("description") or result.get("snippet")
                    ),
                    provider="deepseek",
                )
            )

    return ProviderResponse(
        provider="deepseek",
        answer=answer,
        results=results[:limit],
        model=_text(data.get("model")),
        searched=searched,
    )


class DeepSeekProvider(Provider):
    """DeepSeek Anthropic Messages API with native web search."""

    name = "deepseek"
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

        prompt = search_prompt(
            request.query,
            time_range=request.time_range,
            max_results=request.max_results,
        )
        payload = build_payload(prompt, model)
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode(),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
                "x-api-key": self.api_key,
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
                    error="DeepSeek response JSON must be an object",
                )
            parsed = self.parse(data, max_results=request.max_results)
            parsed.model = _text(data.get("model")) or model
            return parsed
        except urllib.error.HTTPError as exc:
            return ProviderResponse(
                provider=self.name,
                model=model,
                error=f"DeepSeek HTTP {exc.code}",
            )
        except json.JSONDecodeError:
            return ProviderResponse(
                provider=self.name,
                model=model,
                error="DeepSeek returned invalid JSON",
            )
        except TimeoutError:
            return ProviderResponse(
                provider=self.name,
                model=model,
                error="DeepSeek request timed out",
            )
        except urllib.error.URLError:
            return ProviderResponse(
                provider=self.name,
                model=model,
                error="DeepSeek network error",
            )
        except Exception as exc:  # noqa: BLE001 - provider/network errors vary
            return ProviderResponse(
                provider=self.name,
                model=model,
                error=f"DeepSeek {type(exc).__name__}",
            )
