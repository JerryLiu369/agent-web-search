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
DEFAULT_BASE_URL = "https://api.deepseek.com"
API_KEY_ENV = "DEEPSEEK_API_KEY"
BASE_URL_ENV = "AGENT_WEB_SEARCH_DEEPSEEK_BASE_URL"
MODEL_ENV = "AGENT_WEB_SEARCH_DEEPSEEK_MODELS"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _content_blocks(item: dict[str, Any]) -> list[dict[str, Any]]:
    content = item.get("content")
    if isinstance(content, dict):
        return [content]
    if isinstance(content, list):
        return [block for block in content if isinstance(block, dict)]
    return []


def _endpoint(base_url: str) -> str:
    base = base_url.rstrip("/")
    return base if base.endswith("/responses") else f"{base}/responses"


def build_payload(prompt: str, model: str) -> dict[str, Any]:
    return {
        "model": model,
        "input": prompt,
        "tools": [{"type": "web_search"}],
        "tool_choice": {"type": "web_search"},
        "max_output_tokens": 4096,
    }


def parse(data: dict[str, Any], max_results: int = 10) -> ProviderResponse:
    """Parse a DeepSeek Responses API object into the shared provider shape."""
    try:
        limit = max(1, int(max_results))
    except (TypeError, ValueError):
        limit = 10

    answer = ""
    results: list[SearchResult] = []
    seen_urls: set[str] = set()
    searched = False
    output = data.get("output") if isinstance(data, dict) else []
    if not isinstance(output, list):
        output = []

    for item in output:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        searched |= item_type == "web_search_call"
        blocks = _content_blocks(item)
        if item_type in {"output_text", "text"}:
            blocks.append(item)
        for block in blocks:
            if block.get("type") in {"output_text", "text"}:
                text = _text(block.get("text"))
                if text:
                    answer = text
            for annotation in block.get("annotations") or []:
                if not isinstance(annotation, dict):
                    continue
                if annotation.get("type") != "url_citation":
                    continue
                url = _text(annotation.get("url"))
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                results.append(
                    SearchResult(
                        title=_text(annotation.get("title")),
                        url=url,
                        description="",
                        provider="deepseek",
                    )
                )

    if not answer:
        answer = _text(data.get("output_text"))
    return ProviderResponse(
        provider="deepseek",
        answer=answer,
        results=results[:limit],
        model=_text(data.get("model")),
        searched=searched,
    )


class DeepSeekProvider(Provider):
    """DeepSeek Responses API with the native web_search tool."""

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
