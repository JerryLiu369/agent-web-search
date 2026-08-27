from __future__ import annotations

from typing import Any

from .models import SearchResponse

ALL_PROVIDERS_FAILED_CODE = "all_providers_failed"
ALL_PROVIDERS_FAILED_MESSAGE = (
    "All enabled search providers failed. Check provider configuration, "
    "credentials, quotas, and network access."
)


def search_result_payload(result: SearchResponse) -> tuple[dict[str, Any], bool]:
    """Build the shared public payload and error state for every adapter."""
    if result.all_providers_failed:
        return (
            {
                "error": {
                    "code": ALL_PROVIDERS_FAILED_CODE,
                    "message": ALL_PROVIDERS_FAILED_MESSAGE,
                    "provider_errors": result.failed_provider_errors,
                },
                "query": result.query,
            },
            True,
        )
    return result.to_dict(), False
