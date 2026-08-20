"""Native Hermes adapter for Agent Web Search."""

import json

try:
    from .agent_web_search.engine import SearchEngine
    from .agent_web_search.models import SearchRequest
except ImportError:  # Direct validation/test import outside Hermes' plugin namespace.
    from agent_web_search.engine import SearchEngine
    from agent_web_search.models import SearchRequest


def register(ctx):
    schema = {
        "name": "web_search",
        "description": (
            "Multi-provider web search using ARK grounding, DuckDuckGo, and Exa. "
            "Pass a complete natural-language question."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Complete search question."},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
                "max_keyword": {"type": "integer", "minimum": 1, "maximum": 10, "default": 3},
                "time_range": {"type": "string", "enum": ["d", "w", "m", "y"]},
                "providers": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["ark", "ddgs", "exa"]},
                },
            },
            "required": ["query"],
        },
    }
    engine = SearchEngine()

    def handler(args, **kwargs):
        response = engine.search(
            SearchRequest(
                query=args.get("query", ""),
                max_results=args.get("max_results", 10),
                max_keyword=args.get("max_keyword", 3),
                time_range=args.get("time_range"),
                providers=args.get("providers"),
            )
        )
        return json.dumps(response.to_dict(), ensure_ascii=False)

    ctx.register_tool(
        name="web_search",
        toolset="search",
        schema=schema,
        handler=handler,
        emoji="🔎",
        override=True,
        requires_env=["ARK_API_KEY"],
    )