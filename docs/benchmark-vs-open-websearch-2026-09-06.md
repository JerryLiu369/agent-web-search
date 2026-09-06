# Benchmark addendum: head-to-head vs open-webSearch (measured 2026-09-06)

Second run, same day, same three queries. This time against
[open-webSearch](https://github.com/Aas-ee/open-webSearch) (v1.x, the most-starred
free multi-engine search MCP) running its CLI with **every engine enabled**
(`duckduckgo,google,brave,exa,startpage,bing,ddgs`, `--limit 5`), best of two
attempts per query.

## Results

| Query | open-webSearch | agent-web-search (ddgs baseline) | agent-web-search (ark grounding) |
|---|---|---|---|
| Q1 Codex CLI release (EN) | 2.4 s · **1 result** · 4/7 engines failed | 1.2 s · 5 results | 29.8 s · 5 results + answer |
| Q2 中国新能源汽车出口 官方来源 (CN) | 2.2 s · **1 result** (university PDF, not gov.cn) · 4/7 engines failed | 2.6 s · 5 results · 0 gov domains | 22.7 s · 9 results + answer, 海关总署 figures cited |
| Q3 PyTorch 3.0 (EN) | 2.5 s · **1 result** (homepage only) · 4/7 engines failed | 1.2 s · 5 results | 27.7 s · 6 results + answer |

## Honest framing — read before citing

**Server-side caveat (cuts in open-webSearch's favor):** this run happened from
a datacenter IP. open-webSearch scrapes SERP HTML; bing/ddgs/google/brave
engines were bot-walled from that IP (4 of 7 engines returned nothing). From a
residential IP its result counts will be higher. The scraping fragility *is*
the finding — it is inherent to the approach — but the specific 1-result numbers
above are worst-case, not representative of a home user.

**What the comparison does isolate, independent of IP reputation:**

1. **Failure mode shape.** open-webSearch's per-engine scraping degrades
   discretely: an engine is either up (full page of results) or walled (zero).
   API-backed providers degrade gracefully — you get fewer rows, not none.
2. **No synthesis tier.** open-webSearch has no model-native grounding
   equivalent; its output is always a result list. For queries where the
   "official source" constraint matters (Q2), somebody still has to read the
   list. The grounding provider resolves the constraint itself (see main
   benchmark: gov.cn/customs.gov.cn rows + figures + citation).
3. **Rate-limit reality.** Scraped SERPs rate-limit aggressively under agent
   workloads (many queries/hour). API backends bill per call instead. This is
   an architectural property, not an implementation bug — and it is why this
   project treats conventional search as the fallback tier rather than the core.

## Reproducing

```
# open-webSearch side
npx open-websearch@latest search "<query>" --engines duckduckgo,google,brave,exa,startpage,bing,ddgs --limit 5

# agent-web-search side
pipx install agent-web-search-mcp
agent-web-search --provider ddgs --max-results 5 "<query>"
agent-web-search --provider ark --max-results 5 "<query>"   # needs ARK_API_KEY
```

Raw outputs: `docs/benchmark/2026-09-06/` (agent-web-search) and
`docs/benchmark/2026-09-06/ows-q*.txt` (open-webSearch).

---

*Measured 2026-09-06. If you run this comparison and get different numbers,
a PR updating this file with your environment noted is welcome.*
