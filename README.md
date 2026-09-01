<div align="center">

# Agent Web Search

**One web-search core for AI agents, backed by multiple independent providers.**

**English** | [简体中文](https://github.com/JerryLiu369/agent-web-search/blob/main/README.zh-CN.md)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/agent-web-search-mcp.svg)](https://pypi.org/project/agent-web-search-mcp/)
[![CI](https://github.com/JerryLiu369/agent-web-search/actions/workflows/ci.yml/badge.svg)](https://github.com/JerryLiu369/agent-web-search/actions/workflows/ci.yml)
[![MCP 2.x](https://img.shields.io/badge/MCP-2.x-6C47FF)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

<p><strong>One-click remote MCP</strong></p>

<p>
  <a href="https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FJerryLiu369%2Fagent-web-search&amp;env=AGENT_WEB_SEARCH_AUTH_TOKEN"><img alt="Deploy with Vercel" src="https://vercel.com/button" height="34"></a>
  <a href="https://railway.com/new/template?template=https%3A%2F%2Fgithub.com%2FJerryLiu369%2Fagent-web-search&amp;envs=AGENT_WEB_SEARCH_AUTH_TOKEN"><img alt="Deploy on Railway" src="https://railway.com/button.svg" height="34"></a>
  <a href="https://render.com/deploy?repo=https://github.com/JerryLiu369/agent-web-search"><img alt="Deploy to Render" src="https://render.com/images/deploy-to-render-button.svg" height="34"></a>
  <a href="https://zeabur.com/templates/8MQZG0?referralCode=JerryLiu369"><img alt="Deploy on Zeabur" src="https://zeabur.com/button.svg" height="34"></a>
</p>

Works with **Codex CLI**, **Claude Code**, **OpenCode**, **Hermes**, ordinary
shell scripts, Python applications, and remote Streamable HTTP MCP clients.

[Use with an agent](#use-with-an-agent) · [Providers](#providers) ·
[Shared interface](#shared-request-and-response) · [Configuration](#configuration) ·
[Other interfaces](#other-interfaces) · [Troubleshooting](#troubleshooting) ·
[Architecture](ARCHITECTURE.md) · [Development](#development)

</div>

---

Agent Web Search gives an agent two ways to reach the same provider-neutral
search core: a native MCP tool, or a CLI taught through a standard Agent Skill.
Both dispatch enabled providers concurrently, normalize them into one schema,
and isolate provider failures.

```text
Agent ──┬── MCP client ────── web_search ──┐
        │                                  │
        └── Shell + Skill ── CLI command ──┤
                                           ▼
                                      SearchEngine
                                           │
                     DDGS · Exa · Parallel · ARK · Brave
                     Gemini · Grok · Perplexity · Tavily · You.com
```

## Why Agent Web Search

- **Concurrent, independent providers.** All selected providers run at the same
  time, and one provider's failure never discards another provider's results.
- **Zero-key start.** The default providers — DDGS, Exa, and Parallel — work
  without any API key.
- **Two clean agent integrations.** Use MCP for a protocol-native tool, or pair
  the CLI with the included Skill for agents that already have shell access.
- **Focused responses.** Every provider response contains only a generated
  `answer` when available and normalized `results`.
- **No telemetry, no shared secrets.** Provider keys stay in runtime
  environment variables; there is no shared API-key service.

## Providers

> **Free, keyless defaults:** DDGS, Exa, and Parallel all work without an API
> key. Exa and Parallel automatically use their free MCP transports until a
> paid API key is provided.

| Provider | Website | Search backend | API key | Enabled by default |
| --- | --- | --- | --- | :---: |
| **DDGS** | [DuckDuckGo](https://duckduckgo.com) | DuckDuckGo search | **Free · no key required** | Yes |
| **Exa** | [Exa](https://exa.ai) | Paid Search API or free MCP fallback | **Free without key** · optional `EXA_API_KEY` | Yes |
| **Parallel** | [Parallel](https://parallel.ai) | Free MCP or paid LLM-optimized search | **Free without key** · optional `PARALLEL_API_KEY` | Yes |
| **ARK (Recommended)** | [Volcengine Ark](https://www.volcengine.com/product/ark) | Doubao Search | `ARK_API_KEY` | No |
| **Brave** | [Brave Search](https://brave.com/search/api/) | Brave Search API | `BRAVE_SEARCH_API_KEY` | No |
| **Gemini** | [Google AI](https://ai.google.dev/gemini-api/docs/google-search) | Google Search grounding | `GEMINI_API_KEY` | No |
| **Grok** | [xAI](https://docs.x.ai/docs/guides/tools/overview) | xAI web search and X Search | `XAI_API_KEY` | No |
| **Perplexity** | [Perplexity API](https://www.perplexity.ai/api-platform) | Native structured Search API | `PERPLEXITY_API_KEY` | No |
| **Tavily** | [Tavily](https://tavily.com) | Tavily Search API | `TAVILY_API_KEY` | No |
| **You.com** | [You.com API](https://you.com/platform/api) | Unified web and news search | `YDC_API_KEY` | No |

The provider architecture is intentionally open: another search-capable
backend can be added without changing the MCP, Hermes, CLI, or Python-facing
interfaces.

## Use with an agent

**Requirements:** Python 3.10+. The default providers — DDGS, Exa, and
Parallel — need no API key. Choose one integration shape for your agent; both
use the same package and search engine. The PyPI package installs both
`agent-web-search-mcp` and `agent-web-search` commands.

### Option 1: MCP

Choose MCP when the agent supports tool servers and you want typed discovery,
protocol-level errors, or remote access. The same `agent-web-search-mcp`
command supports local stdio and stateless Streamable HTTP.

#### Local stdio MCP

Install the package once:

```bash
# Recommended isolated installation
pipx install agent-web-search-mcp

# Or install into the active Python environment
python -m pip install agent-web-search-mcp
```

Then configure the MCP client to launch `agent-web-search-mcp`:

```json
{
  "mcpServers": {
    "agent-web-search": {
      "command": "agent-web-search-mcp",
      "args": []
    }
  }
}
```

If `uvx` is already available, a client can run the package without a
persistent install by using command `uvx` with args `["agent-web-search-mcp"]`.

<details>
<summary><strong>Codex CLI, Claude Code, and OpenCode examples</strong></summary>

```bash
# Codex CLI
codex mcp add agent-web-search -- agent-web-search-mcp

# Claude Code
claude mcp add agent-web-search -- agent-web-search-mcp
```

OpenCode:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "agent-web-search": {
      "type": "local",
      "command": ["agent-web-search-mcp"],
      "enabled": true
    }
  }
}
```

</details>

#### Remote MCP over HTTPS

Use one of the deployment buttons at the top of this README, or run the same
server yourself:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
export AGENT_WEB_SEARCH_AUTH_TOKEN="replace-with-the-generated-token"
agent-web-search-mcp --transport http
```

The server exposes authenticated `POST /mcp` and public `GET /healthz`. A
remote MCP client connects like this:

```json
{
  "mcpServers": {
    "agent-web-search": {
      "url": "https://your-deployment.example/mcp",
      "headers": {
        "Authorization": "Bearer your-deployment-token"
      }
    }
  }
}
```

Every public deployment must set `AGENT_WEB_SEARCH_AUTH_TOKEN` to at least 32
characters. The server is stateless and does not create `MCP-Session-Id` values.

### Option 2: CLI + Skill

Choose this shape when the agent already has shell access and supports Agent
Skills. The Skill teaches the agent how to invoke the CLI, select controls,
interpret `results`, and handle structured failures; no MCP configuration is
needed.

1. Install the CLI:

   ```bash
   pipx install agent-web-search-mcp
   # Or: python -m pip install agent-web-search-mcp
   ```

2. Install the included [`agent-web-search` Skill](https://github.com/JerryLiu369/agent-web-search/tree/main/skills/agent-web-search):

   ```bash
   npx skills add JerryLiu369/agent-web-search --skill agent-web-search
   ```

   If the agent does not use the `skills` installer, copy
   `skills/agent-web-search` into that client's Skills directory.

3. Verify the CLI, then let the agent search:

   ```bash
   agent-web-search --version
   agent-web-search "What changed in the latest OpenAI Codex CLI?"
   ```

The CLI writes one JSON document to stdout on success. If every provider fails,
it writes the shared `all_providers_failed` JSON to stderr and exits with status
1, so shell-capable agents can distinguish a real failure from empty results.

| CLI option | MCP argument | Values | Default |
| --- | --- | --- | --- |
| positional `QUERY` | `query` | natural-language question | required |
| `--provider` (repeatable) | `providers` | enabled provider names | all enabled |
| `--max-results` | `max_results` | 1–20 | `10` |
| `--max-keyword` | `max_keyword` | 1–10 | `3` |
| `--time-range` | `time_range` | `d`, `w`, `m`, `y` | — |
| `--grok-search-mode` | `grok_search_mode` | `web_search`, `x_search`, `both` | `web_search` |

<details>
<summary><strong>Install the latest development version from GitHub</strong></summary>

```bash
pipx install 'git+https://github.com/JerryLiu369/agent-web-search.git'
```

</details>

> [!IMPORTANT]
> Do not place API keys in shell history, source code, Git commits, screenshots,
> or checked-in MCP configuration. Supply them through server-side or local
> environment variables.

## Shared request and response

MCP exposes one tool named `web_search`; the CLI maps to the same inputs.

| Argument | Type | Required | Default | Description |
| --- | --- | :---: | --- | --- |
| `query` | string | Yes | — | Complete natural-language search question |
| `max_results` | integer, 1–20 | No | `10` | Desired maximum number of results |
| `max_keyword` | integer, 1–10 | No | `3` | Desired maximum number of search queries or keywords |
| `time_range` | `d`, `w`, `m`, `y` | No | — | Past day, week, month, or year |
| `providers` | string array | No | All enabled | Narrow the request to enabled providers |
| `grok_search_mode` | `web_search`, `x_search`, `both` | No | `web_search` | Available only when Grok is enabled |

Example call:

```json
{
  "query": "GPU kernel generation papers from the past month",
  "max_results": 5,
  "time_range": "m",
  "providers": ["ddgs", "exa"]
}
```

Provider selection has two levels:

1. `AGENT_WEB_SEARCH_PROVIDERS` defines the provider set when the process starts.
2. The request-level `providers` argument may narrow that set, but cannot enable
   a provider that was disabled at startup.

### Response format

Each selected provider that succeeds appears under `providers`; failed
providers are omitted:

```json
{
  "query": "GPU kernel generation papers from the past month",
  "providers": {
    "ddgs": {
      "results": [
        {
          "title": "Example result",
          "url": "https://example.com/paper",
          "description": "Excerpt of the matching page",
          "published_at": "2026-08-02"
        }
      ]
    }
  }
}
```

| Field | Meaning |
| --- | --- |
| `answer` | Provider-generated prose answer, when the backend produces one; omitted otherwise |
| `results` | Result rows: `title`, `url`, `description`, plus optional `published_at` and `author` |

If every selected provider fails, MCP returns a tool error. The CLI writes the
same payload to stderr and exits with status 1. Both use the stable code
`all_providers_failed` and include per-provider diagnostics:

```json
{
  "error": {
    "code": "all_providers_failed",
    "message": "All enabled search providers failed. Check provider configuration, credentials, quotas, and network access.",
    "provider_errors": {
      "ddgs": "RuntimeError: rate limited"
    }
  },
  "query": "GPU kernel generation papers from the past month"
}
```

## Python API

The CLI, MCP servers, and Hermes plugin are thin wrappers around
`agent_web_search.SearchEngine`, which is the public Python API.
`SearchRequest` accepts the same fields as the MCP tool arguments:

```python
from agent_web_search import SearchEngine, SearchRequest

engine = SearchEngine()  # reads AGENT_WEB_SEARCH_* variables at construction

response = engine.search(
    SearchRequest(query="latest MCP spec changes", max_results=5, time_range="m")
)

for name, provider in response.providers.items():
    print(f"{name}: searched={provider.searched}, results={len(provider.results)}")

if response.all_providers_failed:
    print(response.failed_provider_errors)
```

## Configuration

Configuration is read from environment variables when the CLI, MCP server, or
Hermes plugin starts. Restart the process after changing provider settings.
See [.env.example](.env.example) for a commented template of every variable.

### General settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `AGENT_WEB_SEARCH_PROVIDERS` | `ddgs,exa,parallel` | Comma-separated startup-enabled provider set |
| `AGENT_WEB_SEARCH_TIMEOUT` | `60` | Socket timeout for a single upstream HTTP call. Multi-step providers multiply it: keyless Parallel makes up to 3 calls (worst case 3×), ARK may append a continuation call (worst case 2×), so the whole search can take up to `3 ×` this value |

Example:

```bash
export AGENT_WEB_SEARCH_PROVIDERS="ddgs,exa,brave"
export AGENT_WEB_SEARCH_TIMEOUT="30"
```

```powershell
$env:AGENT_WEB_SEARCH_PROVIDERS = "ddgs,exa,brave"
$env:AGENT_WEB_SEARCH_TIMEOUT = "30"
```

### HTTP transport settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `AGENT_WEB_SEARCH_MCP_TRANSPORT` | `stdio` | `stdio` or `http`; `--transport` may override it |
| `AGENT_WEB_SEARCH_HTTP_HOST` | `0.0.0.0` | HTTP bind host for container deployments |
| `AGENT_WEB_SEARCH_HTTP_PORT` | `PORT` or `8000` | HTTP bind port; explicit value overrides platform `PORT` |
| `AGENT_WEB_SEARCH_AUTH_TOKEN` | — | Required HTTP Bearer Token, at least 32 characters |
| `AGENT_WEB_SEARCH_ALLOW_ANONYMOUS` | `false` | Explicitly disables HTTP auth for trusted/demo environments |
| `AGENT_WEB_SEARCH_HTTP_ALLOWED_HOSTS` | — | Optional comma-separated Host allowlist |
| `AGENT_WEB_SEARCH_HTTP_ALLOWED_ORIGINS` | — | Optional comma-separated Origin allowlist; requires allowed hosts |
| `AGENT_WEB_SEARCH_HTTP_LOG_LEVEL` | `info` | Uvicorn log level for the container server |

HTTP settings remain environment-only; the deployment files do not introduce
a second application configuration format.

### Provider settings

Default providers are listed first; optional providers then follow alphabetical
order.

#### 1. DDGS

DDGS uses DuckDuckGo and requires no API key or provider-specific environment
variables. The `ddgs` Python dependency is installed with the package.

#### 2. Exa

Exa supports both paid and keyless modes.

| Variable | Required | Purpose |
| --- | :---: | --- |
| `EXA_API_KEY` | No | Uses the paid Search API when present |
| `EXA_MCP_URL` | No | Overrides the free MCP endpoint when no API key is set |

Without `EXA_API_KEY`, Exa falls back to its free MCP endpoint on a best-effort
basis. The paid API generally provides higher quota and reliability.

#### 3. Parallel

Parallel returns information-dense excerpts ranked for LLM context. One
`parallel` provider automatically selects its transport:

- Without a key, it uses Parallel's free Search MCP.
- With `PARALLEL_API_KEY`, it uses the paid Search REST API.

Both transports map `excerpts` into the common result description, so the
calling agent does not need to distinguish `parallel-free` from `parallel`.

| Variable | Required | Purpose |
| --- | :---: | --- |
| `PARALLEL_API_KEY` | No | Enables the paid API; omit it to use the free MCP |

Parallel is enabled by default and its key is optional.

#### 4. ARK (Recommended)

Volcengine ARK uses model-backed search grounding through the Responses API.
Add `ark` to `AGENT_WEB_SEARCH_PROVIDERS` after providing the key.

| Variable | Required | Purpose |
| --- | :---: | --- |
| `ARK_API_KEY` | Yes | One key, or multiple comma/newline-separated keys |
| `AGENT_WEB_SEARCH_ARK_MODELS` | No | Comma/newline-separated ARK model IDs |

One model stays fixed; multiple models are selected round-robin for successive
requests. When multiple ARK keys are configured, a key is selected per request.

<details>
<summary><strong>Optional Volcengine collaboration rewards information</strong></summary>

Agent Web Search does not require participation in a rewards program. ARK users
may optionally review the official
[Volcengine Collaboration Rewards Program](https://www.volcengine.com/docs/82379/1391869?lang=zh).
Quota, supported models, validity periods, and data-authorization terms can
change. Check the official terms before opting in. Participation is not
required to use Agent Web Search.

</details>

#### 5. Brave

| Variable | Required | Purpose |
| --- | :---: | --- |
| `BRAVE_SEARCH_API_KEY` | Yes | Brave Web Search API credential |

Add `brave` to `AGENT_WEB_SEARCH_PROVIDERS` after providing the key.

#### 6. Gemini

| Variable | Required | Purpose |
| --- | :---: | --- |
| `GEMINI_API_KEY` | Yes | Google AI API credential |
| `AGENT_WEB_SEARCH_GEMINI_MODELS` | No | Comma/newline-separated Gemini model IDs |

Gemini maps common result and time controls into best-effort prompt
constraints. One configured model stays fixed; multiple models are selected
round-robin for successive requests.

#### 7. Grok

| Variable | Required | Purpose |
| --- | :---: | --- |
| `XAI_API_KEY` | Yes | xAI API credential |
| `AGENT_WEB_SEARCH_GROK_MODELS` | No | Comma/newline-separated Grok model IDs |

One configured model stays fixed; multiple models are selected round-robin for
successive requests.

When Grok is enabled, the public tool schema adds `grok_search_mode`:

- `web_search` searches the web.
- `x_search` searches X with native date filters when available.
- `both` exposes both server-side tools in one request and lets Grok choose; it
  does not issue two independent model requests.

#### 8. Perplexity

This provider uses Perplexity's native structured Search API. It returns result
rows rather than a Sonar-generated prose answer; OpenRouter compatibility is
intentionally outside this provider's scope.

| Variable | Required | Purpose |
| --- | :---: | --- |
| `PERPLEXITY_API_KEY` | Yes | Perplexity Search API credential |

Add `perplexity` to `AGENT_WEB_SEARCH_PROVIDERS` after providing the key.

#### 9. Tavily

| Variable | Required | Purpose |
| --- | :---: | --- |
| `TAVILY_API_KEY` | Yes | Tavily Search API credential |

Add `tavily` to `AGENT_WEB_SEARCH_PROVIDERS` after providing the key.

#### 10. You.com

You.com returns unified web and news sections. Agent Web Search merges both,
deduplicates URLs, and applies `max_results` to the combined result list.

| Variable | Required | Purpose |
| --- | :---: | --- |
| `YDC_API_KEY` | Yes | You.com Search API credential |

Add `you` to `AGENT_WEB_SEARCH_PROVIDERS` after providing the key.

### Common search controls

Each provider maps the shared controls to its native API when possible and
ignores unsupported controls.

| Provider | `max_results` | `max_keyword` | `time_range` |
| --- | --- | --- | --- |
| DDGS | Native `max_results` | Ignored | Native `timelimit` |
| Exa | Native result count | Ignored | Native publish date |
| Parallel | REST: native `max_results`; keyless MCP: client-side truncation (`results[:max_results]`) | Ignored | Ignored |
| ARK | Native `limit` | Native | Prompt constraint |
| Brave | Native `count` | Ignored | Native `freshness` |
| Gemini | Prompt constraint | Prompt constraint | Prompt constraint |
| Grok | Prompt constraint | Prompt constraint | Prompt; X Search also uses native dates |
| Perplexity | Native `max_results` | Ignored | Native recency filter |
| Tavily | Native `max_results` | Ignored | Native `time_range` |
| You.com | Native `count`, combined cap | Ignored | Native `freshness` |

Prompt-based controls are best-effort and are not strict guarantees.

## Other interfaces

### Native Hermes plugin

Install the native plugin directly from GitHub:

```bash
pip install 'ddgs>=9.0'
hermes plugins install JerryLiu369/agent-web-search --no-enable
hermes plugins enable agent-web-search --allow-tool-override
```

The plugin intentionally replaces Hermes' built-in `web_search` tool, so the
explicit `--allow-tool-override` grant is required. Start a new Hermes session
after enabling it; restart the gateway when using a messaging channel.

Hermes can also connect through its generic MCP integration instead of the
native plugin.

## Troubleshooting

- **`all_providers_failed`** — every selected provider errored. MCP marks the
  call as an error; the CLI writes diagnostics to stderr and exits 1. Check
  keys, quotas, and network access. A single retry may help a transient limit.
- **`agent-web-search` is not found** — install the PyPI package with `pipx` or
  `pip`, then start a new shell so its scripts directory is on `PATH`.
- **HTTP 401 `invalid_token`** — the `Authorization: Bearer …` header must
  match `AGENT_WEB_SEARCH_AUTH_TOKEN`, which must be at least 32 characters.
- **A provider is missing from a response** — failed providers are omitted
  from successful responses. The Python API exposes the reasons in
  `response.failed_provider_errors`.
- **Provider changes have no effect** — provider settings are read once at
  startup; restart the CLI, MCP server, or Hermes plugin after changing them.
- **MCP client times out before the tool returns** —
  `AGENT_WEB_SEARCH_TIMEOUT` bounds a single upstream HTTP call, not the
  whole search. Keyless Parallel issues up to 3 calls and ARK may append a
  continuation request, so the worst case is `3 × AGENT_WEB_SEARCH_TIMEOUT`;
  configure your MCP client's tool timeout accordingly.

## Development

Using [`uv`](https://docs.astral.sh/uv/) keeps the development environment
isolated and reproducible:

```bash
git clone https://github.com/JerryLiu369/agent-web-search.git
cd agent-web-search
uv venv
uv pip install -e '.[dev]'
uv run pytest -q
uv run ruff check .
```

<details>
<summary><strong>Standard venv + pip alternative</strong></summary>

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
pytest -q
ruff check .
```

</details>

[ARCHITECTURE.md](ARCHITECTURE.md) is the design source of truth, and
[AGENTS.md](AGENTS.md) lists the non-negotiable invariants. Read both before
changing transports, configuration, authentication, deployment, providers, or
tool schemas, keep stdio and HTTP behavior identical, and keep `pytest` and
`ruff` green in the same change.

## License

[MIT](LICENSE)
