from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from ..models import ProviderResponse, SearchRequest, SearchResult
from .base import Provider

ENDPOINT = "https://api.x.ai/v1/responses"


class GrokProvider(Provider):
    """xAI Responses API with native web_search or x_search."""

    name = "grok"

    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: float = 60):
        self.api_key = api_key or os.getenv("XAI_API_KEY", "")
        self.model = model or os.getenv("AGENT_WEB_SEARCH_GROK_MODEL", "grok-4.6")
        self.timeout = timeout

    @staticmethod
    def parse(data: dict, tool_name: str = "web_search") -> ProviderResponse:
        answer = ""
        citations: list[SearchResult] = []
        searched = False
        for item in data.get("output") or []:
            item_type = item.get("type", "")
            searched |= item_type in {"web_search_call", "x_search_call"} or tool_name in item_type
            for content in item.get("content") or []:
                if content.get("type") in {"output_text", "text"} and content.get("text", "").strip():
                    answer = content["text"]
                for annotation in content.get("annotations") or []:
                    if annotation.get("type") == "url_citation" and annotation.get("url"):
                        citations.append(SearchResult(
                            title=annotation.get("title", ""),
                            url=annotation["url"],
                            provider="grok",
                        ))
        if not answer and data.get("output_text"):
            answer = data["output_text"]
        unique = {item.url: item for item in citations}
        return ProviderResponse(
            provider="grok",
            answer=answer,
            citations=list(unique.values()),
            model=data.get("model", ""),
            searched=searched,
        )

    def search(self, request: SearchRequest) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(provider=self.name, model=self.model, error="XAI_API_KEY is not set")
        mode = request.grok_search_mode
        if mode not in {"web_search", "x_search", "both"}:
            return ProviderResponse(
                provider=self.name,
                model=self.model,
                error=f"Unsupported grok_search_mode: {mode}",
            )
        tool_names = ["web_search", "x_search"] if mode == "both" else [mode]
        payload = {
            "model": self.model,
            "input": [{"role": "user", "content": request.query}],
            "tools": [{"type": name} for name in tool_names],
        }
        req = urllib.request.Request(
            ENDPOINT,
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                parsed = self.parse(json.loads(response.read().decode()), ",".join(tool_names))
                parsed.model = self.model
                return parsed
        except urllib.error.HTTPError as exc:
            return ProviderResponse(
                provider=self.name,
                model=self.model,
                error=f"Grok HTTP {exc.code}: {exc.read().decode(errors='replace')[:500]}",
            )
        except Exception as exc:  # noqa: BLE001 - provider/network errors vary
            return ProviderResponse(provider=self.name, model=self.model, error=f"Grok {type(exc).__name__}: {exc}")
