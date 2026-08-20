from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import ProviderResponse, SearchRequest, SearchResponse
from .providers import ArkProvider, DDGSProvider, ExaProvider


class SearchEngine:
    def __init__(self, providers=None, timeout: float | None = None):
        timeout = timeout or float(os.getenv("AGENT_WEB_SEARCH_TIMEOUT", "60"))
        all_providers = providers or {
            "ark": ArkProvider(timeout=timeout),
            "ddgs": DDGSProvider(timeout=timeout),
            "exa": ExaProvider(timeout=timeout),
        }
        configured = [
            item.strip()
            for item in os.getenv("AGENT_WEB_SEARCH_PROVIDERS", "ark,ddgs,exa").split(",")
            if item.strip()
        ]
        self.providers = (
            all_providers
            if providers is not None
            else {name: all_providers[name] for name in configured if name in all_providers}
        )

    def search(self, request: SearchRequest) -> SearchResponse:
        query = request.query.strip()
        if not query:
            raise ValueError("query must not be empty")
        selected = request.providers or list(self.providers)
        selected = [x for x in selected if x in self.providers]
        output = {}
        with ThreadPoolExecutor(max_workers=max(1, len(selected))) as pool:
            futures = {
                pool.submit(self.providers[name].search, request): name
                for name in selected
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    output[name] = future.result()
                except Exception as exc:  # noqa: BLE001 - providers must be isolated
                    output[name] = ProviderResponse(
                        provider=name, error=f"{type(exc).__name__}: {exc}"
                    )
        return SearchResponse(
            query=query,
            providers={
                name: output.get(
                    name,
                    ProviderResponse(provider=name, error="provider did not return"),
                )
                for name in selected
            },
        )
