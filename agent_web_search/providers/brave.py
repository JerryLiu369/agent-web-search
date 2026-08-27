from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlencode

from ..models import ProviderResponse, SearchRequest, SearchResult
from .base import Provider

ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
TIME_RANGE_MAP = {"d": "pd", "w": "pw", "m": "pm", "y": "py"}


class BraveProvider(Provider):
    """Brave Web Search API provider."""

    name = "brave"

    def __init__(self, api_key: str | None = None, timeout: float = 60):
        self.api_key = api_key or os.getenv("BRAVE_SEARCH_API_KEY", "")
        self.timeout = timeout

    @staticmethod
    def parse(data: dict) -> ProviderResponse:
        results = [
            SearchResult(
                title=(item.get("title") or "").strip(),
                url=(item.get("url") or "").strip(),
                description=(item.get("description") or "").strip(),
                provider="brave",
            )
            for item in (data.get("web") or {}).get("results") or []
            if isinstance(item, dict) and item.get("url")
        ]
        return ProviderResponse(
            provider="brave", results=results, searched=bool(results)
        )

    def search(self, request: SearchRequest) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(
                provider=self.name, error="BRAVE_SEARCH_API_KEY is not set"
            )
        query = {
            "q": request.query,
            "count": max(1, min(20, request.max_results)),
        }
        if request.time_range in TIME_RANGE_MAP:
            query["freshness"] = TIME_RANGE_MAP[request.time_range]
        req = urllib.request.Request(
            f"{ENDPOINT}?{urlencode(query)}",
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": self.api_key,
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                parsed = self.parse(json.loads(response.read().decode()))
                parsed.searched = True
                return parsed
        except urllib.error.HTTPError as exc:
            return ProviderResponse(
                provider=self.name,
                error=(
                    f"Brave HTTP {exc.code}: "
                    f"{exc.read().decode(errors='replace')[:500]}"
                ),
            )
        except Exception as exc:  # noqa: BLE001 - provider/network errors vary
            return ProviderResponse(
                provider=self.name, error=f"Brave {type(exc).__name__}: {exc}"
            )
