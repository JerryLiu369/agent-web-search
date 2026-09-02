from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import SearchRequest

MAX_QUERY_LENGTH = 4_000

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
    enabled = list(dict.fromkeys(enabled_providers))

    unknown = sorted(set(arguments) - _KNOWN_FIELDS)
    if unknown:
        details.append(
            "unknown argument(s): "
            + ", ".join(unknown)
            + "; allowed: "
            + ", ".join(sorted(_KNOWN_FIELDS))
        )

    query = arguments.get("query")
    if not isinstance(query, str) or not query.strip():
        details.append(
            "query must be a non-empty string"
            + (f", got {type(query).__name__}" if query is not None else "")
        )
    elif len(query) > MAX_QUERY_LENGTH:
        details.append(
            f"query must be at most {MAX_QUERY_LENGTH} characters, got {len(query)}"
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
        details.append(f"time_range must be one of d/w/m/y, got {time_range!r}")

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
            enabled_set = set(enabled)
            names: list[str] = []
            for item in providers:
                if not isinstance(item, str):
                    details.append(
                        f"providers must contain strings, got {type(item).__name__}"
                    )
                else:
                    names.append(item)
            if len(names) != len(dict.fromkeys(names)):
                details.append("providers must not contain duplicate names")
            unavailable = [n for n in names if n not in enabled_set]
            if unavailable:
                details.append(
                    "providers are not enabled: "
                    + ", ".join(dict.fromkeys(unavailable))
                    + "; enabled providers: "
                    + ", ".join(enabled)
                )

    mode = arguments.get("grok_search_mode")
    if mode is not None:
        if "grok" not in enabled:
            details.append("grok_search_mode is only available when grok is enabled")
        elif mode not in {"web_search", "x_search", "both"}:
            details.append(
                "grok_search_mode must be one of web_search/x_search/both, "
                f"got {mode!r}"
            )

    return details


def validate_search_request(
    request: SearchRequest,
    enabled_providers: Any,
) -> list[str]:
    """Validate the public Python request before provider dispatch.

    ``SearchRequest`` has no unknown fields by construction. Its default Grok
    mode is omitted here unless a caller selected a non-default value, matching
    the dynamically generated schema when Grok is disabled.
    """
    arguments: dict[str, Any] = {
        "query": request.query,
        "max_results": request.max_results,
        "max_keyword": request.max_keyword,
        "time_range": request.time_range,
        "providers": request.providers,
    }
    if request.grok_search_mode != "web_search":
        arguments["grok_search_mode"] = request.grok_search_mode
    return validate_web_search_arguments(arguments, enabled_providers)
