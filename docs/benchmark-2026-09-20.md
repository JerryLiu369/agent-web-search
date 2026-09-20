# Benchmark: Model-Native Grounding (Responses & ARK) vs Semantic Search (Exa) vs Conventional SERP (DDGS)

> **Measured Date**: 2026-09-20  
> **Environment**: `agent-web-search` v0.7.5, Python 3.12, Singapore Egress  
> **Verification**: All raw tool invocation payloads are archived in [`docs/benchmark/2026-09-20/`](benchmark/2026-09-20/)

---

## 1. Executive Summary

Most web search aggregators treat LLMs like humans typing into Google: they convert questions into keyword fragments, scrape search engine results pages (SERPs), and hand back 5–10 truncated snippets. 

**This benchmark demonstrates why that paradigm is broken for AI Agents.** When an agent asks a complex technical question or seeks real-time breaking news:
1. **Conventional SERP (DDGS)** returns marketing platitudes and truncated text, forcing the agent to spend another 3–5 tool calls fetching individual web pages (costing significant context tokens and multi-round round-trip latency).
2. **Semantic Vector Search (Exa)** delivers sub-second (~1.2s) precision for official RFCs, PRs, and engineering blogs, bypassing SEO spam farms.
3. **Model-Native Grounding (Responses & ARK)** performs multi-hop retrieval and deep synthesis on the server side, returning an authoritative, fully cited, multi-thousand-word structured brief in **a single tool call**.

---

## 2. Benchmark Queries & Measured Metrics

### Query 1: Deep Technical Architecture
> `"What are the core architectural changes in vLLM V1 engine redesign compared to V0?"`

| Provider | Paradigm | Latency | Result Depth | Downstream Fetch Needed? | Key Findings Delivered |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **DDGS** | Conventional SERP | **2.45 s** | 5 snippets (~120 chars each) | **Yes (5+ calls)** | Generic PR text (*"Building on V0's success, vLLM V1 retains stable components..."*). Zero details on IPC, scheduler, or GIL. |
| **Exa** | Semantic Vector Search | **1.21 s** | 5 structured documents | Optional | Direct hits on RFC `#18571`, official v1-alpha release notes, and Red Hat kernel deep-dives. Zero SEO noise. |
| **Responses** *(Gemini 3.8 Flash)* | Model Grounding (OpenAI Responses) | **32.69 s** | 4,200+ char structured synthesis + 5 sources | **No (0 calls)** | Complete architectural breakdown: `EngineCore` process isolation, `run_busy_loop()` ZeroMQ IPC, unified token-budget scheduling, prefix-cache unification. |
| **ARK** *(Doubao)* | Model Grounding | **31.42 s** | 2,800+ char synthesis + V0/V1 comparison table | **No (0 calls)** | Full comparison table covering batch scheduling differences, token budget dictionaries, and AMD Triton enablement. |

---

### Query 2: Real-time Event & Record Breaking
> `"Who won the 2026 US Open Men singles final, and what records were set in the tournament?"`

| Provider | Paradigm | Latency | Answer Accuracy | Citations |
| :--- | :--- | :--- | :--- | :--- |
| **DDGS** | Conventional SERP | **1.32 s** | ❌ **Failed to answer** (Wikipedia snippets only noted *"final appearance of 2016 champion"*; did not state the winner or score) | Generic Wikipedia index |
| **Exa** | Semantic Vector Search | **3.00 s** | ⚠️ High-quality links, but agent must read articles itself to parse records | BBC Sport, ESPN, ATP Tour |
| **Responses** *(Gemini 3.8 Flash)* | Model Grounding (OpenAI Responses) | **11.98 s** | ✅ **Direct answer + Record analysis**: Alexander Zverev d. Ben Shelton (6-3, 7-6, 5-7, 6-2); 1st German champion in 37 yrs; 3:33 AM latest finish record | Cleanly backfilled domain sources (`usopen.org`, `wikipedia.org`) |

---

## 3. The Real Trade-off: Agent Round-Trips vs Grounding Latency

A common misconception is comparing search provider latency in isolation (e.g. `1.3s` vs `12s`):

```text
[Conventional SERP Workflow]
Agent -> web_search (1.5s) -> receives 5 truncated snippets (unclear answer)
      -> web_extract URL 1 (2.5s)
      -> web_extract URL 2 (2.8s)
      -> web_extract URL 3 (2.2s)
Total Time: ~9.0s | Total Tool Calls: 4 | Context tokens burned: ~18,000

[Model-Native Grounding Workflow]
Agent -> web_search (11.9s) -> receives complete structured answer + precise citations
Total Time: ~11.9s | Total Tool Calls: 1 | Context tokens burned: ~2,500
```

By unifying **Semantic Search (Exa)** for fast discovery and **Model Grounding (Responses / ARK)** for synthesized answers under a single provider-agnostic MCP / CLI contract, `agent-web-search` allows autonomous agents to dynamically choose or aggregate both paradigms without vendor lock-in.

---

## 4. Reproducibility

All benchmarks were run via the CLI interface:

```bash
# Test Semantic Vector Search
agent-web-search --provider exa "What are the core architectural changes in vLLM V1 engine redesign compared to V0?"

# Test Generic OpenAI Responses API with Google Grounding
AGENT_WEB_SEARCH_RESPONSES_BASE_URL="http://127.0.0.1:52718/v1" \
AGENT_WEB_SEARCH_RESPONSES_MODELS="gemini-3.8-flash" \
agent-web-search --provider responses "Who won the 2026 US Open Men singles final, and what records were set in the tournament?"
```
