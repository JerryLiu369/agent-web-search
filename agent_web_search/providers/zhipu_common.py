from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

from ..models import SearchResult

TIME_RANGE_MAP = {
    "d": "oneDay",
    "w": "oneWeek",
    "m": "oneMonth",
    "y": "oneYear",
}


def text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def recency_filter(time_range: str | None) -> str | None:
    return TIME_RANGE_MAP.get(time_range) if time_range is not None else None


def result_limit(value: Any, default: int = 10) -> int:
    try:
        return max(1, min(20, int(value)))
    except (TypeError, ValueError):
        return default


def map_search_results(
    rows: Iterable[Any] | None,
    provider: str,
    max_results: int = 10,
) -> list[SearchResult]:
    """Map Zhipu's result rows to the provider-neutral result model."""
    unique: list[SearchResult] = []
    seen_urls: set[str] = set()
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        url = text(row.get("link") or row.get("url"))
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        unique.append(
            SearchResult(
                title=text(row.get("title")),
                url=url,
                description=text(row.get("content")),
                provider=provider,
                published_at=text(row.get("publish_date")) or None,
            )
        )
    return unique[: result_limit(max_results)]
