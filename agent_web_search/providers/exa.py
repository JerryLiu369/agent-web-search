from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta

from ..models import ProviderResponse, SearchRequest, SearchResult
from .base import Provider


class ExaProvider(Provider):
    name = "exa"

    def __init__(self, endpoint: str | None = None, timeout: float = 60):
        self.endpoint = endpoint or os.getenv("EXA_MCP_URL", "https://mcp.exa.ai/mcp")
        self.timeout = timeout

    @staticmethod
    def parse_text(text: str) -> list[SearchResult]:
        results: list[SearchResult] = []
        for block in text.split("\n\n---\n\n"):
            block = block.strip()
            if not block:
                continue
            fields: dict[str, str] = {}
            description: list[str] = []
            in_highlights = False
            for line in block.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                if ":" in stripped:
                    key, value = stripped.split(":", 1)
                    normalized = key.lower()
                    if normalized in {
                        "title",
                        "url",
                        "published",
                        "author",
                        "highlights",
                    }:
                        fields[normalized] = value.strip()
                        in_highlights = normalized == "highlights"
                        if in_highlights and value.strip():
                            description.append(value.strip())
                        continue
                if in_highlights:
                    description.append(stripped)
            url = fields.get("url", "")
            if url:
                results.append(
                    SearchResult(
                        title=fields.get("title", ""),
                        url=url,
                        description=" ".join(description)[:500],
                        provider="exa",
                        published_at=fields.get("published") or None,
                        author=fields.get("author") or None,
                    )
                )
        return results

    def search(self, request: SearchRequest) -> ProviderResponse:
        args = {
            "query": request.query,
            "num_results": max(1, min(20, request.max_results)),
            "livecrawl": "fallback",
            "type": "magic",
            "use_autoprompt": True,
        }
        if request.time_range in {"d", "w", "m", "y"}:
            days = {"d": 1, "w": 7, "m": 30, "y": 365}[request.time_range]
            args["start_published_date"] = (
                datetime.now(UTC) - timedelta(days=days)
            ).strftime("%Y-%m-%d")
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "web_search_exa", "arguments": args},
        }
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                body = response.read().decode(errors="replace")
            texts = []
            for line in body.splitlines():
                if line.startswith("data: "):
                    try:
                        obj = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    texts += [
                        x.get("text", "")
                        for x in (obj.get("result", {}).get("content") or [])
                        if x.get("type") == "text"
                    ]
            if not texts:
                try:
                    obj = json.loads(body)
                    texts = [
                        x.get("text", "")
                        for x in (obj.get("result", {}).get("content") or [])
                        if x.get("type") == "text"
                    ]
                except json.JSONDecodeError:
                    pass
            results = self.parse_text("\n".join(texts))
            return ProviderResponse(
                provider=self.name, results=results, searched=bool(results)
            )
        except urllib.error.HTTPError as exc:
            return ProviderResponse(
                provider=self.name,
                error=f"Exa HTTP {exc.code}: {exc.read().decode(errors='replace')[:500]}",
            )
        except Exception as exc:  # noqa: BLE001 - remote MCP errors vary
            return ProviderResponse(
                provider=self.name, error=f"Exa {type(exc).__name__}: {exc}"
            )
