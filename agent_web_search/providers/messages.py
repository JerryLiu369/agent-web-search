from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from ..errors import exception_error, http_error
from ..model_pool import RoundRobinModels, configured_models
from ..models import ProviderResponse, SearchRequest, SearchResult
from ..prompting import search_prompt
from .base import Provider

DEFAULT_MODELS = ["claude-3-7-sonnet-20250219", "claude-3-5-haiku-20241022"]
DEFAULT_BASE_URL = "https://api.anthropic.com"
DEFAULT_TOOL_TYPE = "web_search_20250305"
DEFAULT_TOOL_NAME = "web_search"
DEFAULT_TIMEOUT = 60.0

API_KEY_ENV = "AGENT_WEB_SEARCH_MESSAGES_API_KEY"
BASE_URL_ENV = "AGENT_WEB_SEARCH_MESSAGES_BASE_URL"
ENDPOINT_ENV = "AGENT_WEB_SEARCH_MESSAGES_ENDPOINT"
MODEL_ENV = "AGENT_WEB_SEARCH_MESSAGES_MODELS"
TOOL_TYPE_ENV = "AGENT_WEB_SEARCH_MESSAGES_TOOL_TYPE"
TOOL_NAME_ENV = "AGENT_WEB_SEARCH_MESSAGES_TOOL_NAME"
TIMEOUT_ENV = "AGENT_WEB_SEARCH_MESSAGES_TIMEOUT"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _endpoint(base_url: str) -> str:
    base = _text(base_url).rstrip("/")
    if not base:
        return ""
    return base if base.endswith("/v1/messages") else f"{base}/v1/messages"


def _resolve_endpoint(base_url: str | None = None, endpoint: str | None = None) -> str:
    if endpoint is not None:
        return _text(endpoint).rstrip("/")
    if base_url is not None:
        return _endpoint(base_url)
    env_endpoint = _text(os.getenv(ENDPOINT_ENV, ""))
    if env_endpoint:
        return env_endpoint.rstrip("/")
    return _endpoint(os.getenv(BASE_URL_ENV, "") or DEFAULT_BASE_URL)


def _resolve_tool_type(explicit: str | None) -> str:
    if explicit is not None:
        return _text(explicit) or DEFAULT_TOOL_TYPE
    return _text(os.getenv(TOOL_TYPE_ENV, "")) or DEFAULT_TOOL_TYPE


def _resolve_tool_name(explicit: str | None) -> str:
    if explicit is not None:
        return _text(explicit) or DEFAULT_TOOL_NAME
    return _text(os.getenv(TOOL_NAME_ENV, "")) or DEFAULT_TOOL_NAME


def _resolve_timeout(explicit: float | None) -> float:
    raw = _text(os.getenv(TIMEOUT_ENV, ""))
    if raw:
        try:
            override = float(raw)
        except (TypeError, ValueError):
            override = math.nan
        if math.isfinite(override) and override > 0:
            return override
    if explicit is not None:
        return explicit
    return DEFAULT_TIMEOUT


def _domain(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc
    except (TypeError, ValueError):
        return ""


def _content_blocks(block: dict[str, Any]) -> list[dict[str, Any]]:
    content = block.get("content")
    if isinstance(content, list):
        return [item for item in content if isinstance(item, dict)]
    if isinstance(content, dict):
        return [content]
    return []


def build_payload(
    prompt: str,
    model: str,
    tool_type: str = DEFAULT_TOOL_TYPE,
    tool_name: str = DEFAULT_TOOL_NAME,
) -> dict[str, Any]:
    return {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
        "tools": [{"type": tool_type, "name": tool_name, "max_uses": 5}],
    }


def parse(data: dict[str, Any], max_results: int = 10) -> ProviderResponse:
    """Parse a Generic Anthropic Messages response with web search results."""
    try:
        limit = max(1, int(max_results))
    except (OverflowError, TypeError, ValueError):
        limit = 10

    answer_parts: list[str] = []
    results: list[SearchResult] = []
    seen: dict[str, SearchResult] = {}

    def _add_or_backfill(url: str, title: str, description: str = "") -> None:
        existing = seen.get(url)
        if existing is None:
            item = SearchResult(
                title=title, url=url, description=description, provider="messages"
            )
            seen[url] = item
            results.append(item)
        else:
            if not existing.title and title:
                existing.title = title
            if not existing.description and description:
                existing.description = description

    searched = False
    content = data.get("content") if isinstance(data, dict) else []
    if not isinstance(content, list):
        content = []

    for block in content:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if block_type in {"server_tool_use", "tool_use", "web_search_tool_result"}:
            searched = True
        if block_type == "text":
            text = _text(block.get("text"))
            if text:
                answer_parts.append(text)
            citations = block.get("citations")
            if isinstance(citations, list):
                for citation in citations:
                    if not isinstance(citation, dict):
                        continue
                    url = _text(citation.get("url"))
                    if not url:
                        continue
                    _add_or_backfill(
                        url,
                        _text(citation.get("title") or citation.get("document_title")),
                        _text(
                            citation.get("cited_text")
                            or citation.get("description")
                            or citation.get("snippet")
                        ),
                    )
        result_blocks = (
            _content_blocks(block) if block_type == "web_search_tool_result" else []
        )
        if block_type == "web_search_result":
            result_blocks.append(block)
        for result in result_blocks:
            if result.get("type") != "web_search_result":
                continue
            url = _text(result.get("url"))
            if not url:
                continue
            _add_or_backfill(
                url,
                _text(result.get("title")),
                _text(result.get("description") or result.get("snippet")),
            )

    for item in results:
        if not item.title:
            item.title = _domain(item.url)
    if results:
        searched = True

    return ProviderResponse(
        provider="messages",
        answer="\n\n".join(answer_parts),
        results=results[:limit],
        model=_text(data.get("model")) if isinstance(data, dict) else "",
        searched=searched,
    )


class MessagesProvider(Provider):
    """Generic Anthropic Messages API client with a web-search tool."""

    name = "messages"
    parse = staticmethod(parse)

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        endpoint: str | None = None,
        models: list[str] | None = None,
        tool_type: str | None = None,
        tool_name: str | None = None,
        timeout: float | None = None,
    ):
        self.api_key = api_key if api_key is not None else os.getenv(API_KEY_ENV, "")
        self.endpoint = _resolve_endpoint(base_url, endpoint)
        self.models = configured_models(
            models=models,
            env_name=MODEL_ENV,
            defaults=DEFAULT_MODELS,
        )
        self.tool_type = _resolve_tool_type(tool_type)
        self.tool_name = _resolve_tool_name(tool_name)
        self.timeout = _resolve_timeout(timeout)
        self._model_pool = RoundRobinModels(self.models)

    def search(self, request: SearchRequest) -> ProviderResponse:
        model = self._model_pool.next()
        if not self.api_key:
            return ProviderResponse(
                provider=self.name,
                model=model,
                error=f"{API_KEY_ENV} is not set",
            )
        if not self.endpoint:
            return ProviderResponse(
                provider=self.name,
                model=model,
                error=f"{BASE_URL_ENV} is not set",
            )
        prompt = search_prompt(
            request.query,
            time_range=request.time_range,
            max_results=request.max_results,
        )
        payload = build_payload(prompt, model, self.tool_type, self.tool_name)
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
                    error="messages response JSON must be an object",
                )
            parsed = self.parse(data, max_results=request.max_results)
            parsed.model = _text(data.get("model")) or model
            return parsed
        except urllib.error.HTTPError as exc:
            return ProviderResponse(
                provider=self.name,
                model=model,
                error=http_error(self.name, exc.code),
            )
        except Exception as exc:  # noqa: BLE001 - provider/network errors vary
            return ProviderResponse(
                provider=self.name,
                model=model,
                error=exception_error(self.name, exc),
            )
