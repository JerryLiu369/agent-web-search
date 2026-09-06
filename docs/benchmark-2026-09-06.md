# Benchmark: agent-native vs traditional search backends (measured 2026-09-06)

All numbers below were measured on 2026-09-06 with `agent-web-search` v0.7.5, one
CLI invocation per cell, `--max-results 5`, from a server in Singapore. Raw
invocation outputs are reproducible with the commands in the appendix. No
results were edited or cherry-picked; one transient failure was retried once and
noted.

## Latency and result counts by provider

| Provider | Type | Q1: Codex CLI release (EN) | Q2: 中国新能源汽车出口 (CN, 官方来源) | Q3: PyTorch 3.0 (EN) |
|---|---|---|---|---|
| ddgs | conventional SERP | 1.2 s · 5 results | 2.6 s · 5 results | 1.2 s · 5 results |
| exa (free MCP) | semantic search API | 0.3 s · 5 results | 0.4 s · 5 results | 0.4 s · 5 results |
| parallel (free MCP) | context-oriented search | 1.3 s · 5 results | 1.9 s · 5 results | 1.9 s · 5 results |
| ark (Doubao grounding) | model-native grounding | 29.8 s · 5 results + answer | 22.7 s · 9 results + answer | 27.7 s · 6 results + answer |

Q1 = "What changed in the latest OpenAI Codex CLI release?"
Q2 = "2026年中国新能源汽车出口数据 官方来源"
Q3 = "PyTorch 3.0 release date and major features"

## What the numbers show

**Latency vs. synthesis is a real trade-off, not marketing.** The SERP/semantic
backends return in 0.3–2.6 s and hand the *calling agent* five rows to reason
over. ARK's grounding surface took 22–30 s because it decomposes the query,
runs multi-round retrieval, and returns a synthesized answer with citations.
Same tool call, two different points on the latency/depth curve — which is
exactly why this project exposes both behind one interface instead of picking
for you.

**Traditional SERP degrades on natural-language questions.** For Q2 (a
long Chinese question asking for official sources), DDGS returned five rows
but none from gov.cn/customs.gov.cn domains in the top 5 — keyword matching
splits the question into terms and loses the "official source" constraint.
ARK's answer for the same query led with 海关总署 figures (2026 上半年
汽车出口 6358.2亿元, +48.3%) with a working cctv.cn citation, plus a
customs.gov.cn result in the top 3 rows.

**Model-backed providers return `answer` + structured `results`; API
providers return `results` only.** This is by contract, not accident — see
the README's provider taxonomy.

## Reproducing

```
pipx install agent-web-search-mcp   # v0.7.5
export ARK_API_KEY=...              # only needed for the ark row
agent-web-search --provider ark --max-results 5 "2026年中国新能源汽车出口数据 官方来源"
```

Latency will differ by region and time of day; the relative ordering
(semantic API < conventional SERP < grounding) was stable across our runs.

---

*This file is generated from measured runs; the raw per-query outputs are
checked into `docs/benchmark/2026-09-06/` for verification.*
