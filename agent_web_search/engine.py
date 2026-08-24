from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import ProviderResponse, SearchRequest, SearchResponse
from .registry import DEFAULT_PROVIDER_NAMES, create_provider_pool


class SearchEngine:
    def __init__(self, providers=None, timeout: float | None = None):
        timeout = (
            float(os.getenv("AGENT_WEB_SEARCH_TIMEOUT", "60"))
            if timeout is None
            else timeout
        )
        all_providers = (
            create_provider_pool(timeout) if providers is None else providers
        )
        configured = [
            item.strip()
            for item in os.getenv(
                "AGENT_WEB_SEARCH_PROVIDERS", ",".join(DEFAULT_PROVIDER_NAMES)
            ).split(",")
            if item.strip()
        ]
        self._all_providers = all_providers
        self.providers = (
            all_providers
            if providers is not None
            else {
                name: all_providers[name]
                for name in configured
                if name in all_providers
            }
        )

    @property
    def enabled_provider_names(self) -> list[str]:
        return list(self.providers)

    def search(self, request: SearchRequest) -> SearchResponse:
        request = request.normalized()
        query = request.query
        if not query:
            raise ValueError("query must not be empty")
        selected = request.providers or list(self.providers)
        # A request may narrow the startup-enabled set, but cannot enable a
        # provider after registration/schema construction.
        selected = [x for x in selected if x in self.providers]
        output = {}
        with ThreadPoolExecutor(max_workers=max(1, len(selected))) as pool:
            futures = {
                pool.submit(self._all_providers[name].search, request): name
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
        ordered = {
            name: output.get(
                name,
                ProviderResponse(provider=name, error="provider did not return"),
            )
            for name in selected
        }
        return SearchResponse(
            query=query,
            providers={
                name: response
                for name, response in ordered.items()
                if response.error is None
            },
            failed_provider_errors={
                name: response.error
                for name, response in ordered.items()
                if response.error is not None
            },
        )
