# Implementation Report

> **Historical record.** This report describes the change that replaced the
> JavaScript provider fleet with the Python MCP bridge, at a point when the DSH
> suite had 32 tests. Later work — the core `{ query, providers }` payload,
> per-call `max_results` instead of a card setting, no result truncation, and the
> removal of the custom MCP-source path — is reflected in `ARCHITECTURE.md` and
> `integrations/dsh/README.md`, which are the authoritative descriptions. Read
> the statements below as history, not as current behavior.

## Architecture decision

DSH remains the product boundary. The plugin registers one native
`ctx.web` provider and the Cordis patch selects it for DSH's native
`web_search` path, so the model-facing tool name, prompt, citation cards,
settings, history, and diagnostics remain DSH behavior.

The duplicate JavaScript provider fleet and aggregation engine are removed.
Built-in provider attempts now use a short-lived `agent-web-search-mcp` stdio
child and call only the fixed `web_search` operation. The bridge maps DSH live
credential references into the child environment, propagates provider
selection and a caller-supplied `max_results`, bounds output, sanitizes
structured failures, and terminates the child on success, timeout,
cancellation, or malformed output. DSH keeps fanout/fallback orchestration
because those controls and per-source history are not represented in the Python
public MCP response. Custom remote MCP sources were the existing DSH-side
exact-tool path at the time of this change; they were removed later (see the
follow-up section below).

## Files changed

- Added `integrations/dsh/lib/bridge.js` and focused fake-child tests.
- Reworked `integrations/dsh/lib/engine.js` and `provider.js` into the thin
  DSH-to-Python bridge and native result mapper.
- Reduced `integrations/dsh/lib/adapters/index.js` to the custom MCP adapter;
  removed the duplicate built-in JS adapters.
- Added endpoint override environment support to the canonical Python
  providers used by DSH.
- Updated `ARCHITECTURE.md`, root READMEs, and `integrations/dsh/README.md`.
- Replaced provenance tests with bridge/result-contract tests.
- Stripped inherited Exa/Parallel endpoint overrides before spawning the Python
  child and added a regression test for that isolation.
- Documented that Python tests require an installed project environment.

## Verification

- `npm test` — 32 DSH tests passed.
- `uv run --extra dev pytest -q` — 249 Python tests passed.
- Fresh editable install (`uv pip install -e '.[dev]'`) — 249 Python tests
  passed in an isolated environment.
- Fresh wheel build/install (`uv build`, then install into a separate isolated
  environment) — imports for `agent_web_search` and `mcp_types` and both CLI
  entry points passed.
- An isolated environment with only `pytest` and no project install fails with
  the expected `ModuleNotFoundError` for `agent_web_search`; the declared
  package metadata already includes `agent-web-search`, `mcp`, and `mcp-types`,
  so no packaging metadata change was necessary.
- `git diff --check` — passed.
- `node --check` — passed for all DSH JavaScript files.
- No paid provider/API calls were made; bridge tests use fake child processes.

## Remaining limitations

- The Python `agent-web-search-mcp` executable must be installed in the DSH
  host environment, or configured through `AGENT_WEB_SEARCH_MCP_COMMAND`.
- The bridge forces the child transport to `stdio`, even when the DSH host
  environment also contains the Python server's HTTP transport setting.
- DSH custom MCP sources remain HTTP-based and continue to use their existing
  endpoint validation/discovery path; they are intentionally not exposed as
  model-facing MCP tools.
- DDGS uses the canonical Python DDGS backend and does not support replacing
  it with an arbitrary HTML endpoint through the DSH per-source endpoint field.
- The bridge uses one short-lived Python MCP child per built-in provider
  attempt. This preserves exact fanout/fallback and history semantics at the
  cost of process startup overhead.

## Follow-up: custom MCP sources removed

The custom Streamable HTTP MCP-source path described above (the `mcp` provider
kind, `integrations/dsh/lib/adapters/`, the `/api/agent-web-search/mcp-tools`
discovery route, and the settings "MCP tools" tab) was later removed. The
Python core never had a generic MCP consumer, and the DSH adapter intentionally
does not connect arbitrary third-party MCP servers as search providers. What
remains MCP-related is only the internal transport: the bridge spawns the
installed `agent-web-search-mcp` command over local stdio and calls its fixed
`web_search` operation.
