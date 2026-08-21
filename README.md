# Agent Web Search

**Multi-provider web search for AI agents.**

Agent Web Search gives Hermes, Codex CLI, Claude Code, OpenCode, and ordinary scripts one consistent web-search tool. It runs independent providers concurrently and returns normalized results. The default provider set is:

- **ARK grounding** — Volcengine ARK Responses API + `web_search` (Doubao)
- **DDGS** — DuckDuckGo search
- **Exa** — paid Search API with `EXA_API_KEY`, otherwise the free MCP endpoint (best effort)

Optional providers are also implemented:

- **Brave** — Brave Search API with an independent web index and native date filtering
- **Gemini** — Google Search grounding via Gemini Interactions API
- **Grok** — xAI Responses API with native web search and X Search
- **Tavily** — Tavily Search API with native result-count and time-range filters

The architecture is provider-based, so DeepSeek, Brave, and other search-capable providers can be added without changing the MCP or Hermes interfaces.

## Quick start

```bash
# Omit this line when the ARK provider is not enabled.
export ARK_API_KEY="your_ark_api_key"
pipx install 'git+https://github.com/JerryLiu369/agent-web-search.git'
agent-web-search-mcp
```

Do not put API keys in shell history, source code, Git commits, or screenshots. Use a local `.env`/secret manager and export the variable in the process environment.

## Use from Codex CLI

```bash
export ARK_API_KEY="your_ark_api_key"
codex mcp add agent-web-search -- \
  agent-web-search-mcp
codex mcp list
```

## Use from Claude Code

```bash
export ARK_API_KEY="your_ark_api_key"
claude mcp add agent-web-search -- \
  agent-web-search-mcp
```

Or add a project `.mcp.json`:

```json
{
  "mcpServers": {
    "agent-web-search": {
      "command": "agent-web-search-mcp",
      "args": [],
      "env": {"ARK_API_KEY": "${ARK_API_KEY}"}
    }
  }
}
```

## Use from OpenCode

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "agent-web-search": {
      "type": "local",
      "command": ["agent-web-search-mcp"],
      "environment": {"ARK_API_KEY": "${ARK_API_KEY}"},
      "enabled": true
    }
  }
}
```

## Use from Hermes

Install the native plugin directly from GitHub:

```bash
pip install 'ddgs>=9.0'
hermes plugins install JerryLiu369/agent-web-search --no-enable
hermes plugins enable agent-web-search --allow-tool-override
```

The plugin registers the standard `web_search` tool and calls the same
Agent Web Search core used by MCP and CLI. If you prefer the generic MCP path,
Hermes can also connect with `hermes mcp add`.

The GitHub installer installs the package and its optional dependencies:

```bash
pipx install 'git+https://github.com/JerryLiu369/agent-web-search.git'
```

Hermes requires the explicit `--allow-tool-override` grant because this plugin
intentionally replaces its built-in `web_search` tool. Start a new Hermes
session after enabling it; restart the gateway if you use a messaging channel.

## CLI

```bash
agent-web-search "What changed in the latest OpenAI Codex CLI?"
agent-web-search "GPU kernel generation papers from the past month" --time-range m --max-results 5
agent-web-search "latest news" --provider ark --provider ddgs
```

## Volcengine collaboration rewards

Agent Web Search does not require participation in any rewards program. Users who choose to use ARK can create their own API key and optionally review the official **[Volcengine Collaboration Rewards Program](https://www.volcengine.com/docs/82379/1391869?lang=zh)**. The program may provide reward resources according to its current rules, but quota, supported models, validity period, and data authorization terms can change. Check the official page before opting in. Participation means accepting the provider's data-authorization terms; it is not required to use Agent Web Search.

## Configuration

- `ARK_API_KEY`: optional; required only when the ARK provider is enabled. Comma/newline-separated keys are accepted.
- `AGENT_WEB_SEARCH_PROVIDERS`: startup-enabled provider set; default is `ark,ddgs,exa`.
- `AGENT_WEB_SEARCH_TIMEOUT`: per-provider timeout in seconds (default `60`).
- `AGENT_WEB_SEARCH_ARK_MODELS`: comma-separated ARK model IDs.
- `BRAVE_SEARCH_API_KEY`: optional Brave Web Search API key. Add `brave` to `AGENT_WEB_SEARCH_PROVIDERS` to enable it.
- `EXA_API_KEY`: optional; when set, Exa uses the paid Search API (`api.exa.ai/search`) with higher quota and reliability. Without it, Exa falls back to the free MCP endpoint (best effort).
- `EXA_MCP_URL`: optional Exa MCP endpoint override (only used when `EXA_API_KEY` is not set).
- `GEMINI_API_KEY`: optional Gemini provider key.
- `AGENT_WEB_SEARCH_GEMINI_MODEL`: optional Gemini model ID.
- `XAI_API_KEY`: optional Grok provider key.
- `AGENT_WEB_SEARCH_GROK_MODEL`: optional Grok model ID.
- `TAVILY_API_KEY`: optional Tavily provider key.

The provider set is resolved when the Hermes plugin or MCP server starts. The
public `web_search` schema is generated from that set. A request can narrow the
set with `providers`, but cannot activate a provider that was disabled at
startup. If `grok` is startup-enabled, the schema additionally exposes
`grok_search_mode` with `web_search`, `x_search`, and `both` values. `both`
passes both xAI server-side tools in one request and lets Grok decide which to
call; it does not send two independent requests.

### Common search controls

The public interface keeps one provider-neutral set of controls. Each backend
maps them to its native API when possible and silently ignores unsupported
controls:

| Control | ARK | Brave | DDGS | Exa | Gemini / Grok | Tavily |
| --- | --- | --- | --- | --- | --- | --- |
| `max_results` | native `limit` | native `count` | native `max_results` | native `numResults` / `num_results` | English prompt constraint | native `max_results` |
| `max_keyword` | native `max_keyword` | ignored | ignored | ignored | English prompt constraint | ignored |
| `time_range` | English prompt constraint | native `freshness` | native `timelimit` | native publish-date filter | Gemini: prompt; Grok web: prompt; Grok X: native dates + prompt | native `time_range` |

Prompt constraints are best-effort for model-backed providers; they are not
presented as strict guarantees.

## Design principles

- One core, multiple adapters.
- A failed provider does not discard successful providers.
- Provider responses are marked with `searched`, `error`, and `model` instead of pretending every HTTP 200 was a successful search.
- No telemetry and no shared API key service.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev,ddgs,mcp]'
pytest -q
ruff check .
```

## License

MIT.
