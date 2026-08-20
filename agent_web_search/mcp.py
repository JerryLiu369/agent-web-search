from __future__ import annotations

import asyncio
import json

from .engine import SearchEngine
from .models import SearchRequest
from .schema import build_tool_schema


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
        result = engine.search(
            SearchRequest(
                query=args.get("query", ""),
                max_results=args.get("max_results", 10),
                max_keyword=args.get("max_keyword", 3),
                time_range=args.get("time_range"),
                providers=args.get("providers"),
                grok_search_mode=args.get("grok_search_mode", "web_search"),
            )
        )
        return types.CallToolResult(
            content=[types.TextContent(text=json.dumps(result.to_dict(), ensure_ascii=False))]
        )

    server = Server(
        "agent_web_search",
        description="Multi-provider web search for AI agents",
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())
