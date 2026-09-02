"""Native Hermes adapter for Agent Web Search."""

import json

try:
    from .agent_web_search.engine import SearchEngine
    from .agent_web_search.models import SearchRequest
    from .agent_web_search.output import (
        invalid_arguments_payload,
        search_result_payload,
    )
    from .agent_web_search.schema import build_tool_schema
    from .agent_web_search.validation import validate_web_search_arguments
except ImportError:  # Direct validation/test import outside Hermes' plugin namespace.
    from agent_web_search.engine import SearchEngine
    from agent_web_search.models import SearchRequest
    from agent_web_search.output import (
        invalid_arguments_payload,
        search_result_payload,
    )
    from agent_web_search.schema import build_tool_schema
    from agent_web_search.validation import validate_web_search_arguments


def register(ctx):
    engine = SearchEngine()
    schema = build_tool_schema(engine.enabled_provider_names)

    def handler(args, **kwargs):
        problems = validate_web_search_arguments(args, engine.enabled_provider_names)
        if problems:
            return json.dumps(invalid_arguments_payload(problems), ensure_ascii=False)
        try:
            response = engine.search(SearchRequest.from_mapping(args))
        except ValueError as exc:
            return json.dumps(invalid_arguments_payload([str(exc)]), ensure_ascii=False)
        payload, _is_error = search_result_payload(response)
        return json.dumps(payload, ensure_ascii=False)

    ctx.register_tool(
        name="web_search",
        toolset="search",
        schema=schema,
        handler=handler,
        emoji="🔎",
        override=True,
    )
