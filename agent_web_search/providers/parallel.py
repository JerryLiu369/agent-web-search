from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from ..models import ProviderResponse, SearchRequest, SearchResult
from .base import Provider

ENDPOINT = "https://api.parallel.ai/v1/search"
MAX_QUERY_CHARS = 200
MAX_OBJECTIVE_CHARS = 5000


class ParallelProvider(Provider):
    """Parallel Search API provider."""

    name = "parallel"

    def __init__(self, api_key: str | None = None, timeout: float = 60):
        self.api_key = api_key or os.getenv("PARALLEL_API_KEY", "")
        self.timeout = timeout

    @staticmethod
    def parse(data: dict) -> ProviderResponse:
        results: list[SearchResult] = []
        for item in data.get("results") or []:
            if not isinstance(item, dict) or not item.get("url"):
                continue
            excerpts = item.get("excerpts") or []
            if not isinstance(excerpts, list):
                excerpts = []
            description = "\n\n".join(
                str(excerpt).strip()
                for excerpt in excerpts
                if str(excerpt).strip()
            )
            results.append(
                SearchResult(
                    title=(item.get("title") or "").strip(),
                    url=str(item["url"]).strip(),
                    description=description,
                    provider="parallel",
                    published_at=item.get("publish_date") or None,
                )
            )
        return ProviderResponse(provider="parallel", results=results, searched=True)

    def search(self, request: SearchRequest) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(
                provider=self.name,
                error="PARALLEL_API_KEY is not set",
            )
        payload = {
            "objective": request.query[:MAX_OBJECTIVE_CHARS],
            "search_queries": [request.query[:MAX_QUERY_CHARS]],
            "advanced_settings": {
                "max_results": max(1, min(20, request.max_results))
            },
        }
        req = urllib.request.Request(
            ENDPOINT,
            data=json.dumps(payload).encode(),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return self.parse(json.loads(response.read().decode(errors="replace")))
        except urllib.error.HTTPError as exc:
            return ProviderResponse(
                provider=self.name,
                error=f"Parallel HTTP {exc.code}: {exc.reason}",
            )
        except Exception as exc:  # noqa: BLE001 - provider/network errors vary
            return ProviderResponse(
                provider=self.name,
                error=f"Parallel {type(exc).__name__}: {exc}",
            )
