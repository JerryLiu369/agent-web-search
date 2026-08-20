from __future__ import annotations

import json

from .engine import SearchEngine
from .models import SearchRequest


def main():
    from mcp.server import MCPServer

    mcp = MCPServer(
        "agent_web_search",
        description="Multi-provider web search for AI agents",
    )
    engine = SearchEngine()

    @mcp.tool(
        description=(
            "Search the web through multiple providers: "
            "ARK grounding, DuckDuckGo, and Exa."
        )
    )
    def web_search(
        query: str,
        max_results: int = 10,
        max_keyword: int = 3,
        time_range: str | None = None,
        providers: list[str] | None = None,
    ) -> str:
        return json.dumps(
            engine.search(
                SearchRequest(
                    query=query,
                    max_results=max_results,
                    max_keyword=max_keyword,
                    time_range=time_range,
                    providers=providers,
                )
            ).to_dict(),
            ensure_ascii=False,
        )

    mcp.run()
