from __future__ import annotations

import math
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import ProviderResponse, SearchRequest, SearchResponse
from .registry import DEFAULT_PROVIDER_NAMES, create_provider_pool


class SearchEngine:
    def __init__(self, providers=None, timeout: float | None = None):
        if timeout is None:
            raw_timeout = os.getenv("AGENT_WEB_SEARCH_TIMEOUT", "60")
            try:
                timeout = float(raw_timeout)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "AGENT_WEB_SEARCH_TIMEOUT must be a positive number"
                ) from exc
            if not math.isfinite(timeout) or timeout <= 0:
                raise ValueError("AGENT_WEB_SEARCH_TIMEOUT must be a positive number")

        if providers is not None:
            # Explicit provider injection is a test/API escape hatch. Preserve
            # its existing semantics: use the supplied mapping verbatim and
            # ignore AGENT_WEB_SEARCH_PROVIDERS.
            self.providers = providers
        else:
            configured = [
                item.strip()
                for item in os.getenv(
                    "AGENT_WEB_SEARCH_PROVIDERS", ",".join(DEFAULT_PROVIDER_NAMES)
                ).split(",")
                if item.strip()
            ]
            self.providers = create_provider_pool(timeout, configured)

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
