from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections.abc import Sequence

import mcp_types as types
from mcp.server.lowlevel import Server

from . import __version__
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


def create_mcp_server(engine: SearchEngine | None = None) -> Server:
    """Create the shared MCP server used by every transport."""
    engine = engine or SearchEngine()
    schema = build_tool_schema(engine.enabled_provider_names)

    async def list_tools(_ctx, _params) -> types.ListToolsResult:
        return types.ListToolsResult(
            tools=[
                types.Tool(
                    name="web_search",
                    description=schema["description"],
                    inputSchema=schema["parameters"],
                )
            ]
        )

    async def call_tool(_ctx, params) -> types.CallToolResult:
        if params.name != "web_search":
            return types.CallToolResult(
                content=[types.TextContent(text=f"Unknown tool: {params.name}")],
                isError=True,
            )
        args = params.arguments or {}
        request = SearchRequest.from_mapping(args)
        result = await asyncio.to_thread(engine.search, request)
        text, is_error = format_mcp_result(result)
        return types.CallToolResult(
            content=[types.TextContent(text=text)],
            isError=is_error,
        )

    return Server(
        "agent_web_search",
        version=__version__,
        description="Multi-provider web search for AI agents",
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )


async def run_stdio(server: Server | None = None) -> None:
    """Run the shared MCP server over stdin/stdout."""
    from mcp.server.stdio import stdio_server

    server = server or create_mcp_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Multi-provider web search MCP server"
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        help=(
            "MCP transport; defaults to AGENT_WEB_SEARCH_MCP_TRANSPORT or stdio"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = _parser()
    args = parser.parse_args(argv)
    transport = (
        args.transport
        or os.getenv("AGENT_WEB_SEARCH_MCP_TRANSPORT", "stdio")
    ).strip().lower()

    if transport == "stdio":
        asyncio.run(run_stdio())
        return
    if transport == "http":
        from .mcp_http import run_http

        try:
            run_http()
        except ValueError as exc:
            parser.error(str(exc))
        return
    parser.error(
        "AGENT_WEB_SEARCH_MCP_TRANSPORT must be either 'stdio' or 'http'"
    )
