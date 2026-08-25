"""Vercel ASGI entrypoint for stateless MCP Streamable HTTP."""

from .mcp_http import create_http_app

app = create_http_app()
