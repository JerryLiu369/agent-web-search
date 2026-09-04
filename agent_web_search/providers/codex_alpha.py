from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from typing import Any

from .. import __version__
from ..errors import exception_error
from ..models import ProviderResponse, SearchRequest, SearchResult
from .base import Provider

DEFAULT_MODEL = "gpt-5.6-luna"
ENDPOINT_ENV = "AGENT_WEB_SEARCH_CODEX_ALPHA_ENDPOINT"
API_KEY_ENV = "AGENT_WEB_SEARCH_CODEX_ALPHA_API_KEY"
MODEL_ENV = "AGENT_WEB_SEARCH_CODEX_ALPHA_MODEL"
USER_AGENT = f"agent-web-search/{__version__}"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def parse_results(data: dict[str, Any], max_results: int = 10) -> ProviderResponse:
    """Normalize the opaque Alpha ``results`` array into public result rows."""
    try:
        limit = max(1, int(max_results))
    except (OverflowError, TypeError, ValueError):
        limit = 10
    results: list[SearchResult] = []
    for raw in data.get("results") or []:
        if not isinstance(raw, dict):
            continue
        url = _text(raw.get("url"))
        if not url:
            continue
        description = _text(raw.get("description")) or _text(raw.get("snippet"))
        if not description:
            description = _text(raw.get("text"))
        results.append(
            SearchResult(
                title=_text(raw.get("title")),
                url=url,
                description=description,
                provider="codex_alpha",
            )
        )

    output = data.get("output")
    answer = (
        _text(output) if isinstance(output, str) else _text(data.get("output_text"))
    )
    unique: list[SearchResult] = []
    seen: set[str] = set()
    for item in results:
        key = item.url
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return ProviderResponse(
        provider="codex_alpha",
        answer=answer,
        results=unique[:limit],
        model=_text(data.get("model")),
        searched=bool(data.get("results")) or bool(output),
    )


def build_payload(query: str, model: str) -> dict[str, Any]:
    settings: dict[str, Any] = {
        "external_web_access": True,
        "search_context_size": "low",
    }
    return {
        "id": str(uuid.uuid4()),
        "model": model,
        "commands": {"search_query": [{"q": query}]},
        "settings": settings,
    }


class CodexAlphaProvider(Provider):
    """Experimental API-key client for an Alpha Search-compatible gateway."""

    name = "codex_alpha"
    parse = staticmethod(parse_results)

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        model: str | None = None,
        timeout: float = 60,
    ):
        self.api_key = api_key if api_key is not None else os.getenv(API_KEY_ENV, "")
        self.endpoint = (
            endpoint if endpoint is not None else os.getenv(ENDPOINT_ENV, "")
        )
        self.model = model if model is not None else os.getenv(MODEL_ENV, DEFAULT_MODEL)
        self.timeout = timeout

    def search(self, request: SearchRequest) -> ProviderResponse:
        model = self.model
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
                error=f"{ENDPOINT_ENV} is not set",
            )
        payload = build_payload(request.query, model)
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
                data = json.loads(response.read().decode())
            if not isinstance(data, dict):
                raise ValueError("response JSON must be an object")
            parsed = parse_results(data, max_results=request.max_results)
            parsed.model = model
            return parsed
        except urllib.error.HTTPError as exc:
            return ProviderResponse(
                provider=self.name,
                model=model,
                error=f"Codex Alpha HTTP {exc.code}",
            )
        except json.JSONDecodeError:
            return ProviderResponse(
                provider=self.name,
                model=model,
                error="Codex Alpha returned invalid JSON",
            )
        except Exception as exc:  # noqa: BLE001 - provider/network errors vary
            return ProviderResponse(
                provider=self.name,
                model=model,
                error=exception_error("Codex Alpha", exc),
            )
