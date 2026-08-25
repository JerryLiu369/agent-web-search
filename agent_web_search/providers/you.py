from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from ..models import ProviderResponse, SearchRequest, SearchResult
from .base import Provider

ENDPOINT = "https://ydc-index.io/v1/search"
TIME_RANGE_MAP = {"d": "day", "w": "week", "m": "month", "y": "year"}


class YouProvider(Provider):
    """You.com Search API provider."""

    name = "you"

    def __init__(self, api_key: str | None = None, timeout: float = 60):
        self.api_key = api_key or os.getenv("YDC_API_KEY", "")
        self.timeout = timeout

    @staticmethod
    def parse(data: dict, max_results: int = 20) -> ProviderResponse:
        sections = data.get("results") or {}
        candidates = []
        if isinstance(sections, dict):
            for name in ("web", "news"):
                values = sections.get(name) or []
                if isinstance(values, list):
                    candidates.extend(values)

        results: list[SearchResult] = []
        seen_urls: set[str] = set()
        for item in candidates:
            if not isinstance(item, dict):
                continue
            url = (item.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            snippets = item.get("snippets") or []
            if not isinstance(snippets, list):
                snippets = []
            description = "\n\n".join(
                str(snippet).strip()
                for snippet in snippets
                if str(snippet).strip()
            ) or (item.get("description") or "").strip()
            results.append(
                SearchResult(
                    title=(item.get("title") or "").strip(),
                    url=url,
                    description=description,
                    provider="you",
                    published_at=(
                        item.get("page_age")
                        or item.get("published_at")
                        or item.get("date")
                        or None
                    ),
                )
            )
            seen_urls.add(url)
            if len(results) >= max_results:
                break
        return ProviderResponse(provider="you", results=results, searched=True)

    def search(self, request: SearchRequest) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(
                provider=self.name,
                error="YDC_API_KEY is not set",
            )
        max_results = max(1, min(20, request.max_results))
        payload = {"query": request.query, "count": max_results}
        if request.time_range in TIME_RANGE_MAP:
            payload["freshness"] = TIME_RANGE_MAP[request.time_range]
        req = urllib.request.Request(
            ENDPOINT,
            data=json.dumps(payload).encode(),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-API-Key": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode(errors="replace"))
            return self.parse(data, max_results=max_results)
        except urllib.error.HTTPError as exc:
            return ProviderResponse(
                provider=self.name,
                error=f"You.com HTTP {exc.code}: {exc.reason}",
            )
        except Exception as exc:  # noqa: BLE001 - provider/network errors vary
            return ProviderResponse(
                provider=self.name,
                error=f"You.com {type(exc).__name__}: {exc}",
            )
