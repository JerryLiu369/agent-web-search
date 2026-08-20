from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchRequest:
    query: str
    max_results: int = 10
    max_keyword: int = 3
    time_range: str | None = None
    providers: list[str] | None = None


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
