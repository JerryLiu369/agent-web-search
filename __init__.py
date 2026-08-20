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
        response = engine.search(SearchRequest.from_mapping(args))
        return json.dumps(response.to_dict(), ensure_ascii=False)

    ctx.register_tool(
        name="web_search",
        toolset="search",
        schema=schema,
        handler=handler,
        emoji="🔎",
        override=True,
    )
