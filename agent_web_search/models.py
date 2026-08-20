from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchRequest:
    query: str
    max_results: int = 10
    max_keyword: int = 3
    time_range: str | None = None
    providers: list[str] | None = None
    grok_search_mode: str = "web_search"

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> SearchRequest:
        """Create a request from a Hermes or MCP argument mapping."""
        return cls(
            query=values.get("query", ""),
            max_results=values.get("max_results", 10),
            max_keyword=values.get("max_keyword", 3),
            time_range=values.get("time_range"),
            providers=values.get("providers"),
            grok_search_mode=values.get("grok_search_mode", "web_search"),
        )

    def normalized(self) -> SearchRequest:
        """Normalize provider-neutral controls once before dispatch."""

        def bounded(value: Any, default: int, upper: int) -> int:
            try:
                return max(1, min(upper, int(value)))
            except (TypeError, ValueError):
                return default

        providers = None
        if self.providers:
            providers = list(dict.fromkeys(str(name) for name in self.providers))
        return SearchRequest(
            query=str(self.query).strip(),
            max_results=bounded(self.max_results, 10, 20),
            max_keyword=bounded(self.max_keyword, 3, 10),
            time_range=(
                self.time_range if self.time_range in {"d", "w", "m", "y"} else None
            ),
            providers=providers,
            grok_search_mode=str(self.grok_search_mode or "web_search"),
        )


@dataclass
class SearchResult:
    title: str = ""
    url: str = ""
    description: str = ""
    provider: str = ""
    published_at: str | None = None
    author: str | None = None


@dataclass
class ProviderResponse:
    provider: str
    answer: str = ""
    results: list[SearchResult] = field(default_factory=list)
    citations: list[SearchResult] = field(default_factory=list)
    model: str = ""
    error: str | None = None
    searched: bool = False


@dataclass
class SearchResponse:
    query: str
    providers: dict[str, ProviderResponse]

    def to_dict(self) -> dict[str, Any]:
        def result(x: SearchResult) -> dict[str, Any]:
            d = {
                "title": x.title,
                "url": x.url,
                "description": x.description,
                "provider": x.provider,
            }
            if x.published_at:
                d["published_at"] = x.published_at
            if x.author:
                d["author"] = x.author
            return d

        return {
            "query": self.query,
            "providers": {
                k: {
                    "provider": v.provider,
                    "answer": v.answer,
                    "results": [result(x) for x in v.results],
                    "citations": [result(x) for x in v.citations],
                    "model": v.model,
                    "searched": v.searched,
                    **({"error": v.error} if v.error else {}),
                }
                for k, v in self.providers.items()
            },
        }
