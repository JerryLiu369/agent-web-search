from __future__ import annotations

import asyncio
import json

from .engine import SearchEngine
from .models import SearchRequest, SearchResponse
from .schema import build_tool_schema

ALL_PROVIDERS_FAILED_CODE = "all_providers_failed"
ALL_PROVIDERS_FAILED_MESSAGE = (
    "All enabled search providers failed. Check provider configuration, "
    "credentials, quotas, and network access."
)


def format_mcp_result(result: SearchResponse) -> tuple[str, bool]:
    if result.all_providers_failed:
        payload = {
            "error": {
                "code": ALL_PROVIDERS_FAILED_CODE,
                "message": ALL_PROVIDERS_FAILED_MESSAGE,
                "provider_errors": result.failed_provider_errors,
            },
            "query": result.query,
        }
        return json.dumps(payload, ensure_ascii=False), True
    return json.dumps(result.to_dict(), ensure_ascii=False), False


def main():
    import mcp_types as types
    from mcp.server.lowlevel import Server
    from mcp.server.stdio import stdio_server

    engine = SearchEngine()
    schema = build_tool_schema(engine.enabled_provider_names)

    async def list_tools(_ctx, _params):
        return types.ListToolsResult(
            tools=[
                types.Tool(
                    name="web_search",
                    description=schema["description"],
                    inputSchema=schema["parameters"],
                )
            ]
        )

    async def call_tool(_ctx, params):
        if params.name != "web_search":
            return types.CallToolResult(
                content=[types.TextContent(text=f"Unknown tool: {params.name}")],
                isError=True,
            )
        args = params.arguments or {}
        result = engine.search(SearchRequest.from_mapping(args))
        text, is_error = format_mcp_result(result)
        return types.CallToolResult(
            content=[types.TextContent(text=text)],
            isError=is_error,
        )

    server = Server(
        "agent_web_search",
        description="Multi-provider web search for AI agents",
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream, server.create_initialization_options()
            )

    asyncio.run(run())
