from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from ..errors import exception_error, http_error
from ..models import ProviderResponse, SearchRequest, SearchResult
from .base import Provider

ENDPOINT = "https://api.perplexity.ai/search"
TIME_RANGE_MAP = {"d": "day", "w": "week", "m": "month", "y": "year"}


class PerplexityProvider(Provider):
    """Perplexity's native structured Search API provider."""

    name = "perplexity"

    def __init__(self, api_key: str | None = None, timeout: float = 60):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY", "")
        self.timeout = timeout

    @staticmethod
    def parse(data: dict) -> ProviderResponse:
        results = [
            SearchResult(
                title=(item.get("title") or "").strip(),
                url=(item.get("url") or "").strip(),
                description=(item.get("snippet") or "").strip(),
                provider="perplexity",
                published_at=item.get("date") or None,
            )
            for item in data.get("results") or []
            if isinstance(item, dict) and item.get("url")
        ]
        return ProviderResponse(provider="perplexity", results=results, searched=True)

    def search(self, request: SearchRequest) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(
                provider=self.name,
                error="PERPLEXITY_API_KEY is not set",
            )
        payload = {
            "query": request.query,
            "max_results": max(1, min(20, request.max_results)),
        }
        if request.time_range in TIME_RANGE_MAP:
            payload["search_recency_filter"] = TIME_RANGE_MAP[request.time_range]
        req = urllib.request.Request(
            ENDPOINT,
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
                return self.parse(json.loads(response.read().decode(errors="replace")))
        except urllib.error.HTTPError as exc:
            return ProviderResponse(
                provider=self.name,
                error=http_error(self.name, exc.code),
            )
        except Exception as exc:  # noqa: BLE001 - provider/network errors vary
            return ProviderResponse(
                provider=self.name,
                error=exception_error(self.name, exc),
            )
