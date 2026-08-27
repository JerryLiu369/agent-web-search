from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_KNOWN_FIELDS = frozenset(
    {
        "query",
        "max_results",
        "max_keyword",
        "time_range",
        "providers",
        "grok_search_mode",
    }
)


def validate_web_search_arguments(
    arguments: Mapping[str, Any],
    enabled_providers: Any,
) -> list[str]:
    """Validate raw web_search arguments against the tool schema.

    Returns a list of human-readable problems; empty means valid. This is
    the single validation point shared by every transport: the MCP server
    calls it before building a SearchRequest, so stdio and HTTP behave
    identically and the declared inputSchema is actually enforced.
    """
    details: list[str] = []

    unknown = sorted(set(arguments) - _KNOWN_FIELDS)
    if unknown:
        details.append(
            "unknown argument(s): " + ", ".join(unknown)
            + "; allowed: " + ", ".join(sorted(_KNOWN_FIELDS))
        )

    query = arguments.get("query")
    if not isinstance(query, str) or not query.strip():
        details.append(
            "query must be a non-empty string"
            + (f", got {type(query).__name__}" if query is not None else "")
        )

    for name, upper in (("max_results", 20), ("max_keyword", 10)):
        value = arguments.get(name)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int):
            details.append(
                f"{name} must be an integer between 1 and {upper}, "
                f"got {type(value).__name__}"
            )
        elif not 1 <= value <= upper:
            details.append(f"{name} must be between 1 and {upper}, got {value}")

    time_range = arguments.get("time_range")
    if time_range is not None and time_range not in {"d", "w", "m", "y"}:
        details.append(
            f"time_range must be one of d/w/m/y, got {time_range!r}"
        )

    providers = arguments.get("providers")
    if providers is not None:
        if isinstance(providers, str) or not isinstance(providers, (list, tuple)):
            details.append(
                "providers must be an array of provider names, got "
                f"{type(providers).__name__}; pass a list such as "
                '["ddgs"] instead of a bare string'
            )
        elif not providers:
            details.append("providers must contain at least one name")
        else:
            enabled = set(enabled_providers)
            names: list[str] = []
            for item in providers:
                if not isinstance(item, str):
                    details.append(
                        "providers must contain strings, got "
                        f"{type(item).__name__}"
                    )
                else:
                    names.append(item)
            unavailable = [n for n in names if n not in enabled]
            if unavailable:
                details.append(
                    "providers are not enabled: "
                    + ", ".join(dict.fromkeys(unavailable))
                    + "; enabled providers: "
                    + ", ".join(enabled)
                )

    mode = arguments.get("grok_search_mode")
    if mode is not None and mode not in {"web_search", "x_search", "both"}:
        details.append(
            "grok_search_mode must be one of web_search/x_search/both, "
            f"got {mode!r}"
        )

    return details
