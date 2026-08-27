from __future__ import annotations

from collections.abc import Iterable

from .registry import PROVIDER_SPECS


def build_tool_schema(enabled_providers: Iterable[str]) -> dict:
    """Build the public web_search schema from startup-enabled providers."""
    providers = list(dict.fromkeys(enabled_providers))
    properties = {
        "query": {
            "type": "string",
            "minLength": 1,
            "description": "A complete natural-language search question.",
        },
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": 20,
            "default": 10,
            "description": (
                "Desired maximum number of results. Providers "
                "enforce this natively or as a best-effort prompt constraint."
            ),
        },
        "max_keyword": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "default": 3,
            "description": (
                "Desired maximum number of distinct search queries or keywords. "
                "Providers without an equivalent control ignore it."
            ),
        },
        "time_range": {
            "type": "string",
            "enum": ["d", "w", "m", "y"],
            "description": "Optional time filter: past day, week, month, or year.",
        },
        "providers": {
            "type": "array",
            "items": {"type": "string", "enum": providers},
            "minItems": 1,
            "uniqueItems": True,
            "description": "Optional subset of the providers enabled at startup.",
        },
    }
    if "grok" in providers:
        properties["grok_search_mode"] = {
            "type": "string",
            "enum": ["web_search", "x_search", "both"],
            "default": "web_search",
            "description": (
                "Grok-only mode: use web search, X search, or expose both "
                "server-side tools in one request."
            ),
        }
    return {
        "name": "web_search",
        "description": (
            "Search the web through multiple providers. Enabled providers: "
            + "; ".join(
                PROVIDER_SPECS[name].description if name in PROVIDER_SPECS else name
                for name in providers
            )
            + ". Use a complete natural-language question. Failed providers are "
            "omitted from successful responses. If every enabled provider fails, "
            "the call returns a tool error with code all_providers_failed and "
            "per-provider diagnostics."
        ),
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": ["query"],
            "additionalProperties": False,
        },
    }
