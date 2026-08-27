from __future__ import annotations

import contextlib
import json
import os
import urllib.error
import urllib.request
from importlib.metadata import PackageNotFoundError, version
from typing import Any
from uuid import uuid4

from ..models import ProviderResponse, SearchRequest, SearchResult
from .base import Provider

ENDPOINT = "https://api.parallel.ai/v1/search"
MCP_ENDPOINT = "https://search.parallel.ai/mcp"
MCP_PROTOCOL_VERSION = "2025-06-18"
MAX_QUERY_CHARS = 200
MAX_OBJECTIVE_CHARS = 5000
try:
    PACKAGE_VERSION = version("agent-web-search-mcp")
except PackageNotFoundError:
    # Source checkout without an installed distribution: report the in-package
    # version instead of a stale hardcoded number (the old "0.1.0" fallback
    # drifted and made User-Agent traffic lie about the release).
    from .. import __version__ as PACKAGE_VERSION
USER_AGENT = f"agent-web-search/{PACKAGE_VERSION}"


class ParallelProvider(Provider):
    """Parallel Search with free MCP fallback and paid REST when keyed."""

    name = "parallel"

    def __init__(self, api_key: str | None = None, timeout: float = 60):
        self.api_key = api_key or os.getenv("PARALLEL_API_KEY", "")
        self.timeout = timeout

    @staticmethod
    def parse(data: dict) -> ProviderResponse:
        results: list[SearchResult] = []
        for item in data.get("results") or []:
            if not isinstance(item, dict) or not item.get("url"):
                continue
            excerpts = item.get("excerpts") or []
            if not isinstance(excerpts, list):
                excerpts = []
            description = "\n\n".join(
                str(excerpt).strip()
                for excerpt in excerpts
                if str(excerpt).strip()
            )
            results.append(
                SearchResult(
                    title=(item.get("title") or "").strip(),
                    url=str(item["url"]).strip(),
                    description=description,
                    provider="parallel",
                    published_at=item.get("publish_date") or None,
                )
            )
        return ProviderResponse(provider="parallel", results=results, searched=True)

    @staticmethod
    def _request_values(request: SearchRequest) -> tuple[str, list[str], int]:
        return (
            request.query[:MAX_OBJECTIVE_CHARS],
            [request.query[:MAX_QUERY_CHARS]],
            max(1, min(20, request.max_results)),
        )

    def _search_api(self, request: SearchRequest) -> ProviderResponse:
        objective, search_queries, max_results = self._request_values(request)
        payload = {
            "objective": objective,
            "search_queries": search_queries,
            "advanced_settings": {"max_results": max_results},
        }
        req = urllib.request.Request(
            ENDPOINT,
            data=json.dumps(payload).encode(),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            return self.parse(json.loads(response.read().decode(errors="replace")))

    @staticmethod
    def _iter_mcp_messages(text: str) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []

        def emit(value: Any) -> None:
            values = value if isinstance(value, list) else [value]
            messages.extend(item for item in values if isinstance(item, dict))

        body = (text or "").strip()
        if not body:
            return messages
        if body.startswith(("{", "[")):
            with contextlib.suppress(json.JSONDecodeError):
                emit(json.loads(body))
            return messages

        data_lines: list[str] = []

        def flush() -> None:
            if not data_lines:
                return
            with contextlib.suppress(json.JSONDecodeError):
                emit(json.loads("\n".join(data_lines)))
            data_lines.clear()

        for raw_line in body.splitlines():
            line = raw_line.rstrip("\r")
            if line.startswith("data:"):
                data_lines.append(line[len("data:") :].lstrip())
            elif not line.strip():
                flush()
        flush()
        return messages

    @classmethod
    def _select_mcp_envelope(cls, text: str, request_id: str) -> dict[str, Any]:
        fallback: dict[str, Any] = {}
        for message in cls._iter_mcp_messages(text):
            if "result" not in message and "error" not in message:
                continue
            if message.get("id") == request_id:
                return message
            fallback = message
        return fallback

    @staticmethod
    def _extract_mcp_payload(envelope: dict[str, Any]) -> dict[str, Any]:
        if "error" in envelope:
            raise RuntimeError(f"Parallel MCP error: {envelope['error']}")
        result = envelope.get("result")
        if not isinstance(result, dict):
            result = {}
        if result.get("isError"):
            raise RuntimeError(f"Parallel MCP tool error: {result}")
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured
        for block in result.get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "text":
                continue
            try:
                parsed = json.loads(block.get("text") or "")
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        raise RuntimeError("Parallel MCP returned no parseable content")

    def _post_mcp(
        self,
        body: dict[str, Any],
        *,
        session_id: str | None = None,
        protocol_version: str | None = None,
    ) -> tuple[str, str | None]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        if protocol_version:
            headers["MCP-Protocol-Version"] = protocol_version
        req = urllib.request.Request(
            MCP_ENDPOINT,
            data=json.dumps(body).encode(),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            text = response.read().decode(errors="replace")
            transport_session = response.headers.get("Mcp-Session-Id")
        return text, transport_session

    def _search_mcp(self, request: SearchRequest) -> ProviderResponse:
        objective, search_queries, max_results = self._request_values(request)

        initialize_id = str(uuid4())
        initialize_text, transport_session = self._post_mcp(
            {
                "jsonrpc": "2.0",
                "id": initialize_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {
                        "name": "agent-web-search",
                        "version": PACKAGE_VERSION,
                    },
                },
            }
        )
        initialize = self._select_mcp_envelope(initialize_text, initialize_id)
        initialize_result = initialize.get("result")
        protocol_version = (
            initialize_result.get("protocolVersion")
            if isinstance(initialize_result, dict)
            else None
        ) or MCP_PROTOCOL_VERSION

        self._post_mcp(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            session_id=transport_session,
            protocol_version=protocol_version,
        )

        call_id = str(uuid4())
        call_text, _ = self._post_mcp(
            {
                "jsonrpc": "2.0",
                "id": call_id,
                "method": "tools/call",
                "params": {
                    "name": "web_search",
                    "arguments": {
                        "objective": objective,
                        "search_queries": search_queries,
                        "session_id": str(uuid4()),
                    },
                },
            },
            session_id=transport_session,
            protocol_version=protocol_version,
        )
        payload = self._extract_mcp_payload(
            self._select_mcp_envelope(call_text, call_id)
        )
        results = payload.get("results")
        if isinstance(results, list):
            payload = {**payload, "results": results[:max_results]}
        return self.parse(payload)

    def search(self, request: SearchRequest) -> ProviderResponse:
        try:
            return (
                self._search_api(request)
                if self.api_key
                else self._search_mcp(request)
            )
        except urllib.error.HTTPError as exc:
            transport = "API" if self.api_key else "Free MCP"
            return ProviderResponse(
                provider=self.name,
                error=f"Parallel {transport} HTTP {exc.code}: {exc.reason}",
            )
        except Exception as exc:  # noqa: BLE001 - provider/network errors vary
            transport = "API" if self.api_key else "Free MCP"
            return ProviderResponse(
                provider=self.name,
                error=f"Parallel {transport} {type(exc).__name__}: {exc}",
            )
