from __future__ import annotations

import os
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from mcp.server.lowlevel import Server
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .mcp import create_mcp_server

MIN_AUTH_TOKEN_LENGTH = 32
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def _split_values(value: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            item.strip() for item in value.replace("\n", ",").split(",") if item.strip()
        )
    )


def _parse_port(raw: str) -> int:
    try:
        port = int(raw)
    except ValueError as exc:
        raise ValueError("HTTP port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ValueError("HTTP port must be between 1 and 65535")
    return port


@dataclass(frozen=True)
class HTTPSettings:
    host: str
    port: int
    auth_token: str
    allow_anonymous: bool
    allowed_hosts: tuple[str, ...]
    allowed_origins: tuple[str, ...]
    log_level: str

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> HTTPSettings:
        env = os.environ if environ is None else environ
        host = env.get("AGENT_WEB_SEARCH_HTTP_HOST", "0.0.0.0").strip()
        if not host:
            raise ValueError("AGENT_WEB_SEARCH_HTTP_HOST must not be empty")
        raw_port = env.get("AGENT_WEB_SEARCH_HTTP_PORT") or env.get("PORT") or "8000"
        return cls(
            host=host,
            port=_parse_port(raw_port),
            auth_token=env.get("AGENT_WEB_SEARCH_AUTH_TOKEN", "").strip(),
            allow_anonymous=env.get("AGENT_WEB_SEARCH_ALLOW_ANONYMOUS", "")
            .strip()
            .lower()
            in TRUE_VALUES,
            allowed_hosts=_split_values(
                env.get("AGENT_WEB_SEARCH_HTTP_ALLOWED_HOSTS", "")
            ),
            allowed_origins=_split_values(
                env.get("AGENT_WEB_SEARCH_HTTP_ALLOWED_ORIGINS", "")
            ),
            log_level=env.get("AGENT_WEB_SEARCH_HTTP_LOG_LEVEL", "info").strip().lower()
            or "info",
        )


class MCPHTTPPolicyMiddleware:
    """Enforce POST-only JSON MCP and optional deployment-token auth."""

    def __init__(self, app: Any, token: str | None):
        self.app = app
        self._expected = token.encode("utf-8") if token is not None else None

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or scope.get("path", "").rstrip("/") != "/mcp":
            await self.app(scope, receive, send)
            return

        if self._expected is not None:
            headers = dict(scope.get("headers", []))
            authorization = headers.get(b"authorization", b"").decode(
                "latin-1", errors="replace"
            )
            scheme, _, candidate = authorization.partition(" ")
            valid = scheme.lower() == "bearer" and secrets.compare_digest(
                candidate.encode("utf-8"), self._expected
            )
            if not valid:
                response = JSONResponse(
                    {
                        "error": "invalid_token",
                        "error_description": "Authentication required",
                    },
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
                await response(scope, receive, send)
                return

        if scope.get("method") != "POST":
            response = JSONResponse(
                {
                    "error": "method_not_allowed",
                    "error_description": "Stateless MCP accepts POST requests only",
                },
                status_code=405,
                headers={"Allow": "POST"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


async def healthz(_request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "transport": "streamable-http",
            "stateless": True,
        }
    )


def _auth_token(settings: HTTPSettings) -> str | None:
    if settings.auth_token:
        if len(settings.auth_token) < MIN_AUTH_TOKEN_LENGTH:
            raise ValueError(
                "AGENT_WEB_SEARCH_AUTH_TOKEN must be at least "
                f"{MIN_AUTH_TOKEN_LENGTH} characters"
            )
        return settings.auth_token
    if settings.allow_anonymous:
        return None
    raise ValueError(
        "HTTP transport requires AGENT_WEB_SEARCH_AUTH_TOKEN; set "
        "AGENT_WEB_SEARCH_ALLOW_ANONYMOUS=true only for trusted networks "
        "or disposable demos"
    )


def _transport_security(
    settings: HTTPSettings,
) -> TransportSecuritySettings | None:
    if settings.allowed_origins and not settings.allowed_hosts:
        raise ValueError(
            "AGENT_WEB_SEARCH_HTTP_ALLOWED_HOSTS is required when allowed "
            "origins are configured"
        )
    if not settings.allowed_hosts:
        return None
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=list(settings.allowed_hosts),
        allowed_origins=list(settings.allowed_origins),
    )


def create_http_app(
    *,
    settings: HTTPSettings | None = None,
    server: Server | None = None,
) -> Starlette:
    """Create the authenticated stateless Streamable HTTP ASGI app."""
    settings = HTTPSettings.from_env() if settings is None else settings
    server = create_mcp_server() if server is None else server
    auth_token = _auth_token(settings)
    app = server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        host=settings.host,
        transport_security=_transport_security(settings),
        custom_starlette_routes=[
            Route("/healthz", endpoint=healthz, methods=["GET"]),
        ],
    )
    app.add_middleware(MCPHTTPPolicyMiddleware, token=auth_token)
    return app


def run_http() -> None:
    """Run the HTTP transport with uvicorn for container deployments."""
    import uvicorn

    settings = HTTPSettings.from_env()
    app = create_http_app(settings=settings)
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )
