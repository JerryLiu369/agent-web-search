from __future__ import annotations

from collections.abc import Iterable


def build_tool_schema(enabled_providers: Iterable[str]) -> dict:
    """Build the public web_search schema from startup-enabled providers."""
    providers = list(dict.fromkeys(enabled_providers))
    properties = {
        "query": {
            "type": "string",
            "description": "Complete natural-language search question.",
        },
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": 20,
            "default": 10,
        },
        "max_keyword": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "default": 3,
        },
        "time_range": {
            "type": "string",
            "enum": ["d", "w", "m", "y"],
            "description": "Past day, week, month, or year.",
        },
        "providers": {
            "type": "array",
            "items": {"type": "string", "enum": providers},
            "description": "Optional subset of the startup-enabled providers.",
        },
    }
    if "grok" in providers:
        properties["grok_search_mode"] = {
            "type": "string",
            "enum": ["web_search", "x_search", "both"],
            "default": "web_search",
            "description": (
                "Grok-only mode: search the web, search X, or expose both "
                "tools to Grok in the same request."
            ),
        }
    return {
        "name": "web_search",
        "description": (
            "Multi-provider web search. Enabled providers: "
            + ", ".join(providers)
            + ". Pass a complete natural-language question."
        ),
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": ["query"],
        },
    }
