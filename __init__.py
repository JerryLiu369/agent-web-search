"""Native Hermes adapter for Agent Web Search."""

import json

try:
    from .agent_web_search.engine import SearchEngine
    from .agent_web_search.models import SearchRequest
    from .agent_web_search.schema import build_tool_schema
except ImportError:  # Direct validation/test import outside Hermes' plugin namespace.
    from agent_web_search.engine import SearchEngine
    from agent_web_search.models import SearchRequest
    from agent_web_search.schema import build_tool_schema


def register(ctx):
    engine = SearchEngine()
    schema = build_tool_schema(engine.enabled_provider_names)

    def handler(args, **kwargs):
        response = engine.search(
            SearchRequest(
                query=args.get("query", ""),
                max_results=args.get("max_results", 10),
                max_keyword=args.get("max_keyword", 3),
                time_range=args.get("time_range"),
                providers=args.get("providers"),
                grok_search_mode=args.get("grok_search_mode", "web_search"),
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

    )