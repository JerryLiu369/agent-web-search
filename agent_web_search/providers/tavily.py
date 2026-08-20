from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from ..models import ProviderResponse, SearchRequest, SearchResult
from .base import Provider

ENDPOINT = "https://api.tavily.com/search"
TIME_RANGE_MAP = {"d": "day", "w": "week", "m": "month", "y": "year"}


class TavilyProvider(Provider):
    """Tavily Search API provider."""

    name = "tavily"

    def __init__(self, api_key: str | None = None, timeout: float = 60):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")
        self.timeout = timeout

    @staticmethod
    def parse(data: dict) -> ProviderResponse:
        results = [
            SearchResult(
                title=(item.get("title") or "").strip(),
                url=(item.get("url") or "").strip(),
                description=(item.get("content") or "").strip(),
                provider="tavily",
            )
            for item in data.get("results") or []
            if isinstance(item, dict) and item.get("url")
        ]
        return ProviderResponse(
            provider="tavily",
            answer=(data.get("answer") or "").strip(),
            results=results,
            searched=bool(results),
        )

    def search(self, request: SearchRequest) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(
                provider=self.name,
                error="TAVILY_API_KEY is not set",
            )
        payload = {
            "query": request.query,
            "search_depth": "basic",
            "topic": "general",
            "max_results": max(1, min(20, request.max_results)),
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
        }
        if request.time_range in TIME_RANGE_MAP:
            payload["time_range"] = TIME_RANGE_MAP[request.time_range]
        req = urllib.request.Request(
            ENDPOINT,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return self.parse(json.loads(response.read().decode()))
        except urllib.error.HTTPError as exc:
            return ProviderResponse(
                provider=self.name,
                error=(
                    f"Tavily HTTP {exc.code}: "
                    f"{exc.read().decode(errors='replace')[:500]}"
                ),
            )
        except Exception as exc:  # noqa: BLE001 - provider/network errors vary
            return ProviderResponse(
                provider=self.name,
                error=f"Tavily {type(exc).__name__}: {exc}",
            )
