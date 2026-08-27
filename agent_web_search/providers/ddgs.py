from __future__ import annotations

from ..models import ProviderResponse, SearchRequest, SearchResult
from .base import Provider


class DDGSProvider(Provider):
    name = "ddgs"

    def __init__(self, timeout: float = 60):
        self.timeout = timeout

    def search(self, request: SearchRequest) -> ProviderResponse:
        try:
            from ddgs import DDGS
        except ImportError:
            return ProviderResponse(
                provider=self.name,
                error=(
                    "Install the optional dependency: "
                    "pip install 'agent_web_search[ddgs]'"
                ),
            )
        try:
            with DDGS(timeout=self.timeout) as client:
                hits = client.text(
                    request.query,
                    max_results=max(1, min(20, request.max_results)),
                    region="wt-wt",
                    timelimit=request.time_range,
                    safesearch="off",
                    backend="auto",
                )
            results = [
                SearchResult(
                    title=(h.get("title") or "").strip(),
                    url=(h.get("href") or h.get("url") or "").strip(),
                    description=(h.get("body") or h.get("snippet") or "").strip(),
                    provider=self.name,
                )
                for h in hits
                if isinstance(h, dict) and (h.get("href") or h.get("url"))
            ]
            return ProviderResponse(provider=self.name, results=results, searched=True)
        except Exception as exc:  # noqa: BLE001 - third-party backends vary
            return ProviderResponse(
                provider=self.name, error=f"DDGS {type(exc).__name__}: {exc}"
            )
