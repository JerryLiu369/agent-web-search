<div align="center">

# Agent Web Search

**One web-search tool for AI agents, backed by multiple independent providers.**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/agent-web-search-mcp.svg)](https://pypi.org/project/agent-web-search-mcp/)
[![MCP 2.x](https://img.shields.io/badge/MCP-2.x-6C47FF)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Works with **Codex CLI**, **Claude Code**, **OpenCode**, **Hermes**, ordinary
shell scripts, and Python applications.

[Providers](#providers) · [Quick start](#quick-start) ·
[Tool interface](#tool-interface) · [Configuration](#configuration) ·
[Integrations](#integrations) · [Development](#development)

</div>

---

Agent Web Search exposes one provider-neutral `web_search` tool. It dispatches
independent providers concurrently, normalizes their responses, keeps partial
failures isolated, and lets the calling agent choose which enabled providers to
use for each request.

```text
Agent / MCP client
        │
        ▼
    web_search
        │
        ▼
  SearchEngine ──┬── DDGS
                 ├── Exa
                 ├── Parallel
                 ├── ARK
                 ├── Brave
                 ├── Gemini
                 ├── Grok
                 ├── Perplexity
                 ├── Tavily
                 └── You.com
```

## Providers

| Provider | Search backend | API key | Enabled by default |
| --- | --- | --- | :---: |
| **DDGS** | DuckDuckGo search | None | Yes |
| **Exa** | Paid Search API or free MCP fallback | Optional `EXA_API_KEY` | Yes |
| **Parallel** | Free MCP or paid LLM-optimized search | Optional `PARALLEL_API_KEY` | Yes |
| **ARK** | Volcengine ARK Responses API + `web_search` | `ARK_API_KEY` | No |
| **Brave** | Brave Search API | `BRAVE_SEARCH_API_KEY` | No |
| **Gemini** | Google Search grounding | `GEMINI_API_KEY` | No |
| **Grok** | xAI web search and X Search | `XAI_API_KEY` | No |
| **Perplexity** | Native structured Search API | `PERPLEXITY_API_KEY` | No |
| **Tavily** | Tavily Search API | `TAVILY_API_KEY` | No |
| **You.com** | Unified web and news search | `YDC_API_KEY` | No |

The provider architecture is intentionally open: another search-capable
backend can be added without changing the MCP, Hermes, CLI, or Python-facing
interfaces.

## Quick start

Install from PyPI using whichever Python package runner you already have:

```bash
# Standard Python installation
python -m pip install agent-web-search-mcp

# Isolated persistent installation
pipx install agent-web-search-mcp

# Run without a persistent installation
uvx agent-web-search-mcp
```

`pip` and `pipx` install both commands below. `uvx` runs the command named in
its invocation directly.

Run a search without configuring a paid API key after a persistent install:

```bash
agent-web-search "What changed in the latest OpenAI Codex CLI?"
```

Or run the CLI through `uvx` without installing it:

```bash
uvx --from agent-web-search-mcp agent-web-search \
  "What changed in the latest OpenAI Codex CLI?"
```

Or start the stdio MCP server for an MCP client:

```bash
agent-web-search-mcp
```

To use `uvx` directly from an MCP client without installing the package first,
configure the client to run `uvx agent-web-search-mcp`. For example:

```json
{
  "mcpServers": {
    "agent-web-search": {
      "command": "uvx",
      "args": ["agent-web-search-mcp"]
    }
  }
}
```

<details>
<summary><strong>Install the latest development version from GitHub</strong></summary>

```bash
pipx install 'git+https://github.com/JerryLiu369/agent-web-search.git'
```

</details>

> [!IMPORTANT]
> Do not place API keys in shell history, source code, Git commits, screenshots,
> or checked-in MCP configuration. Export them from a secret manager or a local
> environment file that is not committed.

## Tool interface

The MCP server and Hermes plugin register one tool named `web_search`.

| Argument | Type | Required | Default | Description |
| --- | --- | :---: | --- | --- |
| `query` | string | Yes | — | Complete natural-language search question |
| `max_results` | integer, 1–20 | No | `10` | Desired result or citation count |
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

Failed providers are omitted from successful responses. If every selected
provider fails, MCP returns a tool error with the stable code
`all_providers_failed` and includes per-provider diagnostics.

## Configuration

Configuration is read from environment variables when the CLI, MCP server, or
Hermes plugin starts. Restart the process after changing provider settings.

### General settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `AGENT_WEB_SEARCH_PROVIDERS` | `ddgs,exa,parallel` | Comma-separated startup-enabled provider set |
| `AGENT_WEB_SEARCH_TIMEOUT` | `60` | Per-provider timeout in seconds |

Example:

```bash
export AGENT_WEB_SEARCH_PROVIDERS="ddgs,exa,brave"
export AGENT_WEB_SEARCH_TIMEOUT="30"
```

```powershell
$env:AGENT_WEB_SEARCH_PROVIDERS = "ddgs,exa,brave"
$env:AGENT_WEB_SEARCH_TIMEOUT = "30"
```

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

#### 4. ARK

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
| Parallel | Native `max_results` | Ignored | Ignored |
| ARK | Native `limit` | Native | Prompt constraint |
| Brave | Native `count` | Ignored | Native `freshness` |
| Gemini | Prompt constraint | Prompt constraint | Prompt constraint |
| Grok | Prompt constraint | Prompt constraint | Prompt; X Search also uses native dates |
| Perplexity | Native `max_results` | Ignored | Native recency filter |
| Tavily | Native `max_results` | Ignored | Native `time_range` |
| You.com | Native `count`, combined cap | Ignored | Native `freshness` |

Prompt-based controls are best-effort and are not strict guarantees.

## Integrations

### Codex CLI

```bash
codex mcp add agent-web-search -- agent-web-search-mcp
codex mcp list
```

### Claude Code

```bash
claude mcp add agent-web-search -- agent-web-search-mcp
```

Or add a project `.mcp.json`:

```json
{
  "mcpServers": {
    "agent-web-search": {
      "command": "agent-web-search-mcp",
      "args": [],
      "env": {
        "AGENT_WEB_SEARCH_PROVIDERS": "ddgs,exa,parallel"
      }
    }
  }
}
```

### OpenCode

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "agent-web-search": {
      "type": "local",
      "command": ["agent-web-search-mcp"],
      "environment": {
        "AGENT_WEB_SEARCH_PROVIDERS": "ddgs,exa,parallel"
      },
      "enabled": true
    }
  }
}
```

### Hermes

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

## CLI examples

```bash
# Use every startup-enabled provider.
agent-web-search "What changed in the latest OpenAI Codex CLI?"

# Limit results and publication time.
agent-web-search "GPU kernel generation papers" --time-range m --max-results 5

# Select a provider subset for this request.
agent-web-search "latest AI news" --provider ark --provider ddgs
```

## Design principles

- **One core, multiple adapters.** MCP, Hermes, CLI, and Python use the same
  search engine and response models.
- **Independent providers.** A failed provider does not discard successful
  providers; all-provider failure is surfaced explicitly.
- **Transparent execution.** Responses expose `searched` and `model` instead of
  treating every HTTP 200 as a completed search.
- **No shared secrets.** There is no telemetry or shared API-key service.

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

## License

[MIT](LICENSE)
