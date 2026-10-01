# dsh-agent-web-search

`dsh-agent-web-search` is the native DeepSeek Harness integration for
`agent-web-search`. It replaces the implementation behind DSH's native
`web_search` seam while preserving the native tool name, prompt, normalized
sources, and citation cards. It does **not** install or expose an
`mcp__...__web_search` model tool.

The bundle also replaces the model-facing tool itself: the shipped
`{ queries }` schema cannot express the MCP operation contract, so the
`tool-web` row is switched to `search: false` (keeping `web_fetch`) and this
plugin registers its own `web_search` with the same parameters as the Python
operation — `query`, `max_results`, `time_range`, `providers`, and
`grok_search_mode`. All of them are per-call inputs, exactly as in the Python
operation: `max_results` is **not** a DSH setting. When the model omits it, the
bridge omits it too and the core default (5) applies; `time_range` and
`grok_search_mode` are per-call only. Agent presets mount their own `tool-web`
row, which no patch layer can reach, so the tool is additionally registered
inside every agent scope (`lib/agent-tool.js`) with `force: true` to shadow the
shipped one there.

## Architecture

- DSH registers exactly one `ctx.web` provider: `agent-web-search`.
- The Cordis patch pins the shared `web` seam to that provider and disables the
  built-in DeepSeek search row without changing the tool surface.
- Built-in providers are delegated to the installed Python
  `agent-web-search-mcp` command over local stdio. The bridge calls only the
  fixed `web_search` MCP operation, bounds output, forwards `max_results` when
  the caller set one, honors cancellation and timeouts, and terminates the child
  process.
- The bridge never truncates what an upstream returned: `max_results` bounds
  what each upstream is *asked* for, and the core already applies it. DSH keeps
  every returned row (unsafe URLs rejected, duplicates optionally collapsed).
- DSH retains its fanout/fallback strategy controls, live credentials,
  in-memory history, diagnostics, and settings page.

The Python package must be installed in the same environment as the DSH host:

```bash
python -m pip install agent-web-search-mcp
```

Use `AGENT_WEB_SEARCH_MCP_COMMAND` when the executable is not on DSH's `PATH`.
`AGENT_WEB_SEARCH_MCP_ARGS` may contain a JSON array of extra command-line
arguments. The bridge always invokes the fixed `web_search` operation and never
passes provider credentials as MCP arguments.

## Installation

Full steps, including the desktop app, the Python runtime, and a copy-paste
install prompt, live in [docs/INSTALL.md](./docs/INSTALL.md). The short form:

```bash
dsh plugin --profile <profile> add github:JerryLiu369/agent-web-search
python -m pip install agent-web-search-mcp
```

The desktop app ships its own `dsh plugin` command, which manages the desktop
profile directly — no manual file placement is needed. Restart DSH after
installation if the new provider is not picked up immediately.

If another bundle writes the `web.searchProvider` value later, its layer wins.
Keep this bundle last, or restate `searchProvider: agent-web-search` in the
profile-owned Cordis patch. The patch also repeats `fetchProvider: http` so the
whole-row replacement does not discard the existing fetch provider.

## Settings and credentials

The existing **Settings → agent-web-search** page remains available. Its
controls retain the following runtime behavior:

- `fanout` and `fallback` execution modes;
- provider enablement/order, per-attempt timeout, total timeout, URL
  de-duplication, and answer inclusion;
- per-upstream model text for model-backed upstreams (DeepSeek, Gemini, Grok,
  ARK, Zhipu chat search, generic Messages/Responses, Codex Alpha):
  comma-separated model names, blank means the backend default;
- native tool type/name overrides for the generic Messages backend and tool
  type override for the Responses backend; blank means the backend default;
- DSH credential references, which are resolved server-side and never persisted
  in the provider queue or sent to the model; and
- bounded in-memory call history and authenticated diagnostics.

`time_range` and `grok_search_mode` are per-call tool arguments with no card
equivalent. The tool schema itself is built from the enabled queue at agent
creation: `grok_search_mode` appears only when grok is enabled and `providers`
is constrained to the enabled set, exactly like the Python operation.

Codex Alpha ships disabled: besides its API key it also needs its gateway
endpoint in the per-source endpoint field before it can serve.

Built-in provider credentials use the canonical Python environment names listed
in the root README. DSH resolves the corresponding credential reference into
the child process environment for one search and removes unrelated credential
variables from that child. Restart DSH after changing environment variables.

The per-source endpoint field accepts HTTPS URLs, or HTTP URLs on loopback for
local fakes and development. Embedded credentials and URL fragments are
rejected. The field is offered only for the kinds whose Python provider actually
reads an endpoint variable, so DDGS — which drives the `ddgs` library directly —
does not show it, rather than collecting a value nothing can apply.

## Native result and error behavior

The native model-facing `web_search` result preserves the Python/MCP success
contract exactly: `{ query, providers }`. Each provider entry keeps its optional
`answer` and `results` rows, including `published_at` and `author` when present.
No row is discarded to shorten the payload: `max_results` bounds what each
upstream is asked for and the core already applies it. Rows whose URL is not a
safe navigable web URL (non-HTTP, credentialed, or fragment-bearing) are dropped
one by one rather than failing the provider, so untrusted upstream data cannot
turn a single bad row into a denial of service. An all-provider failure is
returned as the structured `{ error, query }` envelope with
`error.code = "all_providers_failed"` and sanitized `provider_errors`.

DSH citation cards are a separate presentation projection: they may add source
labels, deduplicate URLs, and expose an optional answer without mutating the
model-facing payload. Malformed MCP output, oversized output, timeout,
cancellation, and other provider failures remain sanitized DSH execution errors;
upstream response bodies and credentials are never copied into model-visible
errors or history.

### The citation row

The client half registers its own `tool.call.toolview` for `web_search` at a lower
slot priority than the shipped row, which is how the slot ledger says to shadow
an occupied key (same priority would throw). This is not optional decoration: DSH's
built-in web row builds a citation card only when the *call arguments* carry its
own `{ queries }` array, and this plugin deliberately keeps the MCP operation's
`query` argument instead, so the shipped row always declines and the
conversation falls back to the raw JSON result. The replacement accepts our
argument shape, and hands the sources to DSH's own `WebBlock` so the citation
list matches the built-in card; if that client module is not reachable it renders
the same list with local styles, and for a running call, a failure, or a result
with no card metadata it shows the same raw text the shipped row would have.

The internal bridge uses local stdio only.

## Development and verification

From the repository root:

```bash
npm test
uv run --extra dev pytest -q
```

The Python tests require the project and its development dependencies to be
installed. Running `python -m pytest` from an uninstalled checkout is expected
to fail with missing-module errors; it does not represent a package defect.
For a standard virtual environment, use `python -m pip install -e '.[dev]'`
before running `pytest -q`.

The DSH bridge tests use fake child processes and never make paid provider
requests. They cover result mapping, malformed and structured error results,
per-call `max_results` forwarding (and its omission), URL safety and dedupe,
cancellation, timeout, bounded output, and child cleanup.

The package layout is intentionally a thin DSH adapter. Provider dispatch,
normalization, credentials, and shared failure payloads belong to the Python
`SearchEngine`, not a second JavaScript provider fleet.
