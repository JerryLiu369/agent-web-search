from __future__ import annotations

from collections.abc import Iterable

PROVIDER_DESCRIPTIONS = {
    "ark": "Volcengine ARK web search (Doubao)",
    "ddgs": "DuckDuckGo web search",
    "exa": "Exa web search",
    "gemini": "Gemini Google Search grounding",
    "grok": "Grok web search and X Search",
    "tavily": "Tavily web search",
}


def build_tool_schema(enabled_providers: Iterable[str]) -> dict:
    """Build the public web_search schema from startup-enabled providers."""
    providers = list(dict.fromkeys(enabled_providers))
    properties = {
        "query": {
            "type": "string",
            "description": "A complete natural-language search question.",
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
            "description": "Optional time filter: past day, week, month, or year.",
        },
        "providers": {
            "type": "array",
            "items": {"type": "string", "enum": providers},
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
            + "; ".join(PROVIDER_DESCRIPTIONS.get(name, name) for name in providers)
            + ". Use a complete natural-language question."
        ),
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": ["query"],
        },
    }
