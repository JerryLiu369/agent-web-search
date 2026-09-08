---
name: agent-web-search
description: Search the live web through the agent-web-search CLI — powered by model-native search grounding and agent search backends. Optimized for complete natural-language questions rather than keyword fragments when online sources or cross-provider web research are needed.
---

# Agent Web Search CLI

Use the installed `agent-web-search` command as the search interface. This is
the shell-native alternative to the project's MCP tool; it uses the same search
engine, providers, inputs, response shape, and all-provider failure payload.

## Core Characteristic: Model-Native Search & Natural-Language Queries

**Agent Web Search is fundamentally built around model-native search grounding and agent-facing semantic search services, NOT traditional keyword SERP scrapers.**

- **Always pass complete natural-language questions**: Formulate your query as a full sentence with explicit context, goals, and constraints.
- **Do NOT use fragmented keyword queries**: Avoid short Google/Baidu-style keywords (e.g. do **NOT** search `"NVIDIA earnings Q3"` or `"DeepSeek V3 benchmark"`).
- **Why this matters**: Upstream model providers (`ark`, `deepseek`, `gemini`, `grok`, `zhipu_chat_search`) and semantic search engines (`exa`, `parallel`) use neural models to read, reason, and ground citations. Feeding them fragmented keywords deprives the model of semantic context and severely degrades grounding and synthesis quality.

| Query Style | Example | Result Quality |
| :--- | :--- | :--- |
| **Recommended (Natural Language)** | `agent-web-search "What were the key revenue highlights and datacenter guidance from NVIDIA's latest earnings report?"` | High-signal answer with precise URL citations |
| **Avoid (Keyword Fragments)** | `agent-web-search "NVIDIA earnings report revenue"` | Degraded model grounding, generic SERP noise |

## Before searching

- Confirm the command is available with `agent-web-search --version` when its
  installation state is unknown.
- If it is missing, follow the project's installation instructions. Do not
  perform a persistent package installation unless the user requested setup or
  has otherwise authorized it.
- When setup is authorized, install the published package with either
  `python -m pip install agent-web-search-mcp` or
  `pipx install agent-web-search-mcp`; both install the `agent-web-search`
  and `agent-web-search-mcp` entry points.
- Provider configuration and credentials come from environment variables.
  Never put provider API keys in command arguments, output, or chat messages.

## Provider selection and configuration

Set `AGENT_WEB_SEARCH_PROVIDERS` to the comma-separated startup set. A repeated
`--provider` can only narrow that set; it cannot enable a provider that was not
registered at startup. The current Provider IDs are:

- **Traditional search:** `ddgs` (no key).
- **Model-native search:** `ark` (`ARK_API_KEY`), `codex_alpha`
  (`AGENT_WEB_SEARCH_CODEX_ALPHA_API_KEY` plus its endpoint), `deepseek`
  (`DEEPSEEK_API_KEY`), `gemini` (`GEMINI_API_KEY`), `grok` (`XAI_API_KEY`),
  and `zhipu_chat_search` (`ZHIPU_CHAT_SEARCH_API_KEY`).
- **Agent search:** `brave` (`BRAVE_SEARCH_API_KEY`), `exa` (`EXA_API_KEY`
  or its configured free MCP endpoint), `parallel` (`PARALLEL_API_KEY` or
  its configured free MCP endpoint), `perplexity` (`PERPLEXITY_API_KEY`),
  `tavily` (`TAVILY_API_KEY`), `you` (`YDC_API_KEY`), and
  `zhipu_web_search` (`ZHIPU_WEB_SEARCH_API_KEY`).

Provider-specific model and endpoint overrides, HTTP settings, and the complete
placeholder environment template are in `.env.example`. For the two Zhipu
surfaces, configure them independently, for example:

```bash
AGENT_WEB_SEARCH_PROVIDERS=zhipu_web_search
ZHIPU_WEB_SEARCH_API_KEY=<server-side-key>
agent-web-search "智谱最近发布了哪些新的模型能力和开发工具？" --provider zhipu_web_search
```

Use `zhipu_chat_search` instead when a model-generated answer is wanted; it uses
`ZHIPU_CHAT_SEARCH_API_KEY` and optionally
`AGENT_WEB_SEARCH_ZHIPU_CHAT_MODELS`. Never use a shared `ZHIPU_API_KEY`
fallback or pass either credential as a CLI/MCP argument.

## Run a search

Pass one complete natural-language question as the positional argument:

```bash
agent-web-search "What changes were introduced in the latest MCP protocol specification?"
```

Use common controls only when the request benefits from them:

```bash
agent-web-search "What are the latest research papers and techniques on GPU kernel generation using Triton?" --time-range m --max-results 5
agent-web-search "What major AI model announcements happened in the open-source community this week?" --provider ddgs --provider exa
agent-web-search "What are developers currently discussing about MCP client implementations on X?" --provider grok --grok-search-mode x_search
```

- `--provider` is repeatable and can only narrow providers enabled through
  `AGENT_WEB_SEARCH_PROVIDERS`. Omit it when the enabled set is unknown. The
  CLI rejects unavailable names as a usage error instead of returning an
  ambiguous empty result.
- Queries are limited to 4,000 characters. `--max-results` accepts 1-20.
- `--time-range` accepts `d`, `w`, `m`, or `y`.
- Prefer the default provider set for general research. DDGS, Exa, and Parallel
  work without keys by default. Use a named paid provider only when the user
  requested it or the environment is known to enable it.
- ARK is the recommended model-backed provider when a generated synthesis is
  useful. DeepSeek uses the Anthropic-compatible Messages API with native web
  search when its API key is configured; select it with `--provider deepseek`.
  Grok's `x_search` is appropriate for X-specific requests.

Keep the query a single shell argument. Use the shell's normal quoting rules;
do not interpolate untrusted query text into a larger executable command.

## Interpret the result

On success, exit status is `0` and stdout is one JSON document:

```json
{
  "query": "...",
  "providers": {
    "ddgs": {
      "results": [
        {
          "title": "...",
          "url": "https://example.com",
          "description": "..."
        }
      ]
    }
  }
}
```

- Treat `results` as the primary evidence. When combining providers, deduplicate
  results by URL and retain useful source diversity.
- `answer` is optional provider-generated prose. Treat it as a synthesis, not
  as a replacement for the supporting URLs in `results`.
- Failed providers are omitted when at least one provider succeeds. Do not
  claim that an omitted requested provider succeeded.
- Cite or link the actual result URLs when reporting researched facts.

## Handle failures

If every selected provider fails, the CLI exits with status `1`, writes no
success document to stdout, and writes JSON to stderr with code
`all_providers_failed` and `provider_errors` diagnostics.

Argument or usage errors exit with status `2`.

Use the diagnostics to distinguish missing credentials, quotas, timeouts, and
network failures. A single bounded retry is reasonable for a transient timeout
or rate limit. If the same failure repeats, report it instead of retrying
indefinitely or silently switching to an unrelated search mechanism.
