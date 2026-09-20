from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.request
from typing import Any

from .. import __version__
from ..errors import exception_error, http_error
from ..model_pool import RoundRobinModels, configured_models
from ..models import ProviderResponse, SearchRequest, SearchResult
from ..prompting import search_prompt
from .base import Provider

DEFAULT_MODELS = ["gpt-4o"]
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_TOOL_TYPE = "web_search"
DEFAULT_TIMEOUT = 60.0

BASE_URL_ENV = "AGENT_WEB_SEARCH_RESPONSES_BASE_URL"
# Deprecated alias kept for backward compatibility; prefer BASE_URL_ENV.
ENDPOINT_ENV = "AGENT_WEB_SEARCH_RESPONSES_ENDPOINT"
API_KEY_ENV = "AGENT_WEB_SEARCH_RESPONSES_API_KEY"
MODEL_ENV = "AGENT_WEB_SEARCH_RESPONSES_MODELS"
TOOL_TYPE_ENV = "AGENT_WEB_SEARCH_RESPONSES_TOOL_TYPE"
TIMEOUT_ENV = "AGENT_WEB_SEARCH_RESPONSES_TIMEOUT"

USER_AGENT = f"agent-web-search/{__version__}"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _endpoint(base_url: str) -> str:
    base = _text(base_url).rstrip("/")
    if not base:
        return ""
    if base.endswith("/responses"):
        return base
    if base.endswith("/v1"):
        return f"{base}/responses"
    return f"{base}/v1/responses"


def _resolve_base_url(base_url: str | None, endpoint: str | None = None) -> str:
    if base_url is not None:
        return base_url
    if endpoint is not None:
        return endpoint
    env = os.getenv(BASE_URL_ENV, "") or os.getenv(ENDPOINT_ENV, "")
    return env if _text(env) else DEFAULT_BASE_URL


def _resolve_api_key(explicit: str | None) -> str:
    if explicit is not None:
        return explicit
    return os.getenv(API_KEY_ENV, "") or os.getenv("OPENAI_API_KEY", "")


def _resolve_tool_type(explicit: str | None) -> str:
    if explicit is not None:
        return _text(explicit) or DEFAULT_TOOL_TYPE
    return _text(os.getenv(TOOL_TYPE_ENV, "")) or DEFAULT_TOOL_TYPE


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


def build_payload(prompt: str, model: str, tool_type: str) -> dict[str, Any]:
    return {
        "model": model,
        "input": prompt,
        "tools": [{"type": tool_type}],
    }


def parse(
    data: dict[str, Any],
    max_results: int = 10,
    tool_type: str = DEFAULT_TOOL_TYPE,
) -> ProviderResponse:
    """Parse an OpenAI Responses API payload with a web-search tool call."""
    try:
        limit = max(1, int(max_results))
    except (OverflowError, TypeError, ValueError):
        limit = 10

    answer_parts: list[str] = []
    results: list[SearchResult] = []
    seen_urls: set[str] = set()
    searched = False

    output = data.get("output") if isinstance(data, dict) else []
    if not isinstance(output, list):
        output = []

    for item in output:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type", "")
        if not isinstance(item_type, str):
            continue
        if "web_search_call" in item_type or (tool_type and tool_type in item_type):
            searched = True
            action = item.get("action")
            sources = action.get("sources") if isinstance(action, dict) else []
            if not isinstance(sources, list):
                continue
            for source in sources:
                if not isinstance(source, dict):
                    continue
                url = _text(source.get("url"))
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                results.append(
                    SearchResult(
                        title=_text(source.get("title")),
                        url=url,
                        provider="responses",
                    )
                )

    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        contents = item.get("content") or []
        if isinstance(contents, dict):
            contents = [contents]
        if not isinstance(contents, list):
            continue
        for content in contents:
            if not isinstance(content, dict):
                continue
            if content.get("type") in {"output_text", "text"}:
                text = _text(content.get("text"))
                if text:
                    answer_parts.append(text)
            annotations = content.get("annotations") or []
            if not isinstance(annotations, list):
                continue
            for annotation in annotations:
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
                        provider="responses",
                    )
                )

    answer = "\n\n".join(answer_parts)
    if not answer and isinstance(data.get("output_text"), str):
        answer = _text(data.get("output_text"))
    if results:
        searched = True

    return ProviderResponse(
        provider="responses",
        answer=answer,
        results=results[:limit],
        model=_text(data.get("model")),
        searched=searched,
    )


class ResponsesProvider(Provider):
    """Generic OpenAI Responses API client with a web-search tool."""

    name = "responses"
    parse = staticmethod(parse)

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        endpoint: str | None = None,
        models: list[str] | None = None,
        tool_type: str | None = None,
        timeout: float | None = None,
    ):
        self.api_key = _resolve_api_key(api_key)
        configured_base_url = _resolve_base_url(base_url, endpoint)
        self.endpoint = _endpoint(configured_base_url)
        self.models = configured_models(
            models=models,
            env_name=MODEL_ENV,
            defaults=DEFAULT_MODELS,
        )
        self.tool_type = _resolve_tool_type(tool_type)
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
        payload = build_payload(prompt, model, self.tool_type)
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
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
                    error="responses response JSON must be an object",
                )
            parsed = self.parse(
                data,
                max_results=request.max_results,
                tool_type=self.tool_type,
            )
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
