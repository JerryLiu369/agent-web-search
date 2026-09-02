# Architecture

This document is the design source of truth for Agent Web Search. Changes to
transports, configuration, authentication, deployment, or public interfaces
must preserve the invariants below or update this document in the same change.

## Product shape

Agent Web Search is one provider-neutral search core with thin adapters:

```text
                         SearchEngine
                              │
              shared schema / request / response
                              │
        ┌──────────┬──────────┼──────────┬──────────┐
        ▼          ▼          ▼          ▼          ▼
     Python       CLI     MCP stdio   MCP HTTP    Hermes
       API                              HTTPS      plugin
```

The adapters must not implement their own provider dispatch, response models,
tool schema, or failure semantics.

Each public provider response contains at most `answer` and `results`; `answer`
is omitted when the provider produces no prose. `results`
is the sole normalized source list for every provider. Model-backed providers
may also return `answer`; URLs supporting that answer are normalized into
`results`. Result rows never repeat the provider name that is already the
enclosing dictionary key — the payload goes straight into an LLM context, so
redundant fields have a real token cost. Rich, span-level citations and
execution metadata are internal and out of scope for the public response until
explicitly designed.

## Agent integration shapes

The project has two first-class ways for an agent to use the same search core:

1. **MCP:** `agent-web-search-mcp` exposes `web_search` over local stdio or
   authenticated, stateless Streamable HTTP.
2. **CLI + Skill:** an agent with shell access follows
   `skills/agent-web-search/SKILL.md` and invokes `agent-web-search` directly.

The Skill is an instruction layer, not a second search implementation. It does
not own configuration, provider dispatch, response normalization, or retry
state. The CLI and MCP reuse the same request model, search engine, success
payload, and `all_providers_failed` error payload.

On CLI success, stdout contains one JSON response and the process exits with
status 0. If every provider fails, stderr contains the shared structured error
payload and the process exits with status 1. Argument errors use status 2.

## Public interfaces

- `agent-web-search QUERY` runs a direct CLI search.
- `skills/agent-web-search/SKILL.md` teaches shell-capable agents to use that
  CLI without introducing another runtime or configuration layer.
- `agent-web-search-mcp` starts MCP over stdio by default.
- `agent-web-search-mcp --transport http` starts the same MCP server over
  Streamable HTTP.
- `agent_web_search.mcp_http:create_http_app` exposes the ASGI application for
  serverless platforms.
- The Hermes plugin and Python API call the same `SearchEngine` directly.

MCP stdio and MCP HTTP expose the same `web_search` tool, input schema, output
shape, provider selection, partial-failure behavior, and
`all_providers_failed` error. They are two transports, not two products.

## Configuration

Runtime configuration is environment-only. The project does not introduce a
YAML, TOML, or JSON application configuration file.

- Provider selection, credentials, models, and timeouts use the existing
  `AGENT_WEB_SEARCH_*` and provider-specific environment variables.
- HTTP host, port, authentication, and transport security also use environment
  variables.
- `query`, `providers`, `max_results`, and `time_range` are
  request inputs, not persistent configuration.
- A command-line transport selector is allowed because it chooses the process
  operating mode; the equivalent environment variable must also exist for
  deployment platforms.

## MCP transports

### stdio

- Remains the default for backward compatibility.
- Uses stdin/stdout JSON-RPC and does not listen on a network port.
- Does not add application-layer authentication; the local OS user and process
  boundary provide access control.
- Must never write logs or diagnostics to stdout.

### Streamable HTTP

- Uses the MCP SDK's Streamable HTTP transport at `POST /mcp`.
- Is stateless and returns JSON responses.
- Does not create or persist `MCP-Session-Id` values.
- Does not require a database, Redis, event store, or sticky sessions.
- Exposes unauthenticated `GET /healthz` for platform health checks.
- Uses HTTPS externally; deployment platforms may terminate TLS before sending
  HTTP to the ASGI application.

The initial HTTP mode does not add a separate REST `/search` API, SSE
resumability, subscriptions, or server-initiated notifications.

## HTTP authentication

- `/mcp` requires a static Bearer Token by default.
- The server token comes from `AGENT_WEB_SEARCH_AUTH_TOKEN`.
- Each request is authenticated independently; credentials never create server
  session state.
- Tokens are accepted only through the `Authorization` header and are compared
  in constant time.
- `AGENT_WEB_SEARCH_ALLOW_ANONYMOUS=true` is an explicit opt-out intended for
  trusted networks and disposable demos.
- `/healthz` remains public and never calls an upstream provider.
- Provider API keys remain server-side environment variables and are never MCP
  tool arguments.

OAuth, user accounts, per-user secret storage, quotas, billing, and a shared
hosted SaaS are separate future product decisions. They are not part of the
self-hosted HTTP server.

## Deployment boundary

All platforms run the same ASGI application and differ only in their launch
adapter:

- Vercel imports the ASGI application as a stateless function.
- Railway, Render, Zeabur, Koyeb, Fly.io, and generic Docker run the MCP command
  in HTTP mode and bind to the platform-provided port.
- Cloud Run runs the same container with request-driven scaling.

Zeabur's `template.yaml` is a deployment descriptor only. It selects the
existing HTTP transport and supplies environment variables; it does not add a
second application configuration format.

The shared deployment contract is:

```text
POST /mcp
GET  /healthz
Authorization: Bearer <AGENT_WEB_SEARCH_AUTH_TOKEN>
```

Deployment templates may describe environment variables and startup commands,
but must not introduce a second application configuration format.

## Compatibility and testing

Every transport change must verify:

1. stdio remains the zero-argument default.
2. HTTP is stateless and protected by default.
3. `GET /healthz` works without authentication.
4. stdio and HTTP use the same MCP server factory and tool schema.
5. missing or invalid HTTP credentials are rejected.
6. all-provider failure remains an MCP tool error with code
   `all_providers_failed`.
7. schema-invalid `web_search` arguments (empty query, wrong types, unknown
   providers, out-of-range values, unknown fields) return a structured tool
   error with code `invalid_arguments` on both stdio and HTTP.
8. Python 3.10 through 3.13 and Ruff remain green.
9. CLI success stays on stdout with status 0; all-provider failure stays on
   stderr with the shared payload and status 1.
10. The bundled Agent Skill passes structural validation and documents the
    current CLI contract.

## Explicit non-goals for the first HTTP release

- A second MCP implementation for HTTP.
- A custom REST search API.
- Persistent MCP sessions or a shared state store.
- OAuth or multi-tenant credential management.
- Client-supplied provider API keys.
- Anonymous public access by default.
