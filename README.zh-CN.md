<div align="center">

# Agent Web Search

**面向 AI Agent 的统一联网搜索核心，由多个相互独立的 Provider 提供支持。**

[English](https://github.com/JerryLiu369/agent-web-search/blob/main/README.md) | **简体中文**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/agent-web-search-mcp.svg)](https://pypi.org/project/agent-web-search-mcp/)
[![CI](https://github.com/JerryLiu369/agent-web-search/actions/workflows/ci.yml/badge.svg)](https://github.com/JerryLiu369/agent-web-search/actions/workflows/ci.yml)
[![MCP 2.x](https://img.shields.io/badge/MCP-2.x-6C47FF)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

<p><strong>一键部署远程 MCP</strong></p>

<p>
  <a href="https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FJerryLiu369%2Fagent-web-search&amp;env=AGENT_WEB_SEARCH_AUTH_TOKEN"><img alt="Deploy with Vercel" src="https://vercel.com/button" height="34"></a>
  <a href="https://railway.com/new/template?template=https%3A%2F%2Fgithub.com%2FJerryLiu369%2Fagent-web-search&amp;envs=AGENT_WEB_SEARCH_AUTH_TOKEN"><img alt="Deploy on Railway" src="https://railway.com/button.svg" height="34"></a>
  <a href="https://render.com/deploy?repo=https://github.com/JerryLiu369/agent-web-search"><img alt="Deploy to Render" src="https://render.com/images/deploy-to-render-button.svg" height="34"></a>
  <a href="https://zeabur.com/templates/8MQZG0?referralCode=JerryLiu369"><img alt="Deploy on Zeabur" src="https://zeabur.com/button.svg" height="34"></a>
</p>

支持 **Codex CLI**、**Claude Code**、**OpenCode**、**Hermes**、普通命令行脚本、Python 应用和远程 Streamable HTTP MCP 客户端。

[给 Agent 使用](#给-agent-使用) · [搜索服务](#搜索服务) ·
[统一接口](#统一请求与响应) · [配置](#配置) · [其他接口](#其他接口) ·
[故障排查](#故障排查) · [架构](ARCHITECTURE.md) · [开发](#开发)

</div>

---

Agent Web Search 为 Agent 提供两种接入同一个搜索核心的方式：原生 MCP
工具，或者由标准 Agent Skill 教会 Agent 调用 CLI。两种方式都会并发调用
已启用的 Provider、归一化响应，并隔离单个 Provider 的失败。

```text
Agent ──┬── MCP 客户端 ───── web_search ──┐
        │                                 │
        └── Shell + Skill ── CLI 命令 ────┤
                                          ▼
                                     SearchEngine
                                          │
                    DDGS · Exa · Parallel · ARK · Brave
                    Gemini · Grok · Perplexity · Tavily · You.com
```

## 为什么选择 Agent Web Search

- **并发且相互独立。** 所有选中的 Provider 同时发起请求，单个 Provider 失败不会丢弃其他 Provider 的成功结果。
- **零 Key 即可上手。** 默认 Provider（DDGS、Exa、Parallel）无需任何 API Key。
- **两种清晰的 Agent 接入。** 需要协议原生工具时用 MCP；已有 Shell 能力的 Agent 则使用 CLI + Skill。
- **响应聚焦。** 每个 Provider 响应仅包含可用时的文本 `answer` 和统一的 `results`。
- **无遥测、不共享密钥。** Provider Key 只存在于运行环境变量中，项目不提供任何共享 API Key 服务。

## 搜索服务

> **默认免费、无需 Key：** DDGS、Exa 和 Parallel 都可以不配置 API Key
> 直接使用。Exa 和 Parallel 只有在提供付费 API Key 后才会切换到付费接口，
> 否则自动使用免费 MCP。

| Provider | 搜索后端 | API Key | 默认启用 |
| --- | --- | --- | :---: |
| **DDGS** | DuckDuckGo 搜索 | **免费 · 无需 Key** | 是 |
| **Exa** | 付费 Search API 或免费 MCP 后备 | **无 Key 免费** · 可选 `EXA_API_KEY` | 是 |
| **Parallel** | 免费 MCP 或面向 LLM 优化的付费搜索 | **无 Key 免费** · 可选 `PARALLEL_API_KEY` | 是 |
| **ARK（推荐）** | 火山引擎 ARK Responses API + `web_search` | `ARK_API_KEY` | 否 |
| **Brave** | Brave Search API | `BRAVE_SEARCH_API_KEY` | 否 |
| **Gemini** | Google Search grounding | `GEMINI_API_KEY` | 否 |
| **Grok** | xAI 网页搜索和 X Search | `XAI_API_KEY` | 否 |
| **Perplexity** | 原生结构化 Search API | `PERPLEXITY_API_KEY` | 否 |
| **Tavily** | Tavily Search API | `TAVILY_API_KEY` | 否 |
| **You.com** | 统一网页与新闻搜索 | `YDC_API_KEY` | 否 |

Provider 架构是开放的：添加新的搜索后端时，不需要修改 MCP、Hermes、CLI 或 Python 接口。

## 给 Agent 使用

**环境要求：** Python 3.10+。默认的 DDGS、Exa 和 Parallel 都无需 API
Key。请为 Agent 选择一种接入形态；两者使用的是同一个包和搜索引擎。PyPI
包会同时安装 `agent-web-search-mcp` 和 `agent-web-search` 两个命令。

### 形态一：MCP

当 Agent 支持工具服务器，或者你需要类型化的工具发现、协议级错误、远程
访问时，选择 MCP。同一个 `agent-web-search-mcp` 命令同时支持本地 stdio
和无状态 Streamable HTTP。

#### 本地 stdio MCP

先安装一次：

```bash
# 推荐：隔离安装
pipx install agent-web-search-mcp

# 或安装到当前 Python 环境
python -m pip install agent-web-search-mcp
```

然后让 MCP 客户端启动 `agent-web-search-mcp`：

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

如果本机已经有 `uvx`，也可以不持久安装，让客户端使用命令 `uvx`、参数
`["agent-web-search-mcp"]`。

<details>
<summary><strong>Codex CLI、Claude Code 和 OpenCode 示例</strong></summary>

```bash
# Codex CLI
codex mcp add agent-web-search -- agent-web-search-mcp

# Claude Code
claude mcp add agent-web-search -- agent-web-search-mcp
```

OpenCode：

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

#### 远程 HTTPS MCP

可以直接使用 README 顶部的一键部署按钮，也可以自行运行同一个服务器：

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
export AGENT_WEB_SEARCH_AUTH_TOKEN="替换为刚生成的-token"
agent-web-search-mcp --transport http
```

服务器提供需要鉴权的 `POST /mcp` 和公开的 `GET /healthz`。远程 MCP
客户端这样连接：

```json
{
  "mcpServers": {
    "agent-web-search": {
      "url": "https://你的部署域名.example/mcp",
      "headers": {
        "Authorization": "Bearer 你的部署-token"
      }
    }
  }
}
```

所有公网部署都必须设置至少 32 个字符的 `AGENT_WEB_SEARCH_AUTH_TOKEN`。
服务端无状态，不会创建 `MCP-Session-Id`。

### 形态二：CLI + Skill

当 Agent 已经有 Shell 能力并支持 Agent Skills 时，选择这个形态。Skill
会教 Agent 调用 CLI、选择控制参数、理解 `results` 并处理结构化失败，不需要
配置 MCP Server。

1. 安装 CLI：

   ```bash
   pipx install agent-web-search-mcp
   # 或：python -m pip install agent-web-search-mcp
   ```

2. 安装仓库内的 [`agent-web-search` Skill](https://github.com/JerryLiu369/agent-web-search/tree/main/skills/agent-web-search)：

   ```bash
   npx skills add JerryLiu369/agent-web-search --skill agent-web-search
   ```

   如果 Agent 不使用 `skills` 安装器，就把 `skills/agent-web-search` 复制到
   对应客户端的 Skills 目录。

3. 验证 CLI，然后让 Agent 搜索：

   ```bash
   agent-web-search --version
   agent-web-search "OpenAI Codex CLI 最新版本有哪些变化？"
   ```

CLI 成功时向 stdout 写入一个 JSON 文档。如果所有 Provider 都失败，它会向
stderr 写入统一的 `all_providers_failed` JSON，并以状态码 1 退出，因此 Agent
可以区分真正的失败和空结果。

| CLI 选项 | MCP 参数 | 取值 | 默认值 |
| --- | --- | --- | --- |
| 位置参数 `QUERY` | `query` | 自然语言问题 | 必填 |
| `--provider`（可重复） | `providers` | 已启用的 Provider 名 | 所有已启用 |
| `--max-results` | `max_results` | 1–20 | `10` |
| `--max-keyword` | `max_keyword` | 1–10 | `3` |
| `--time-range` | `time_range` | `d`、`w`、`m`、`y` | — |
| `--grok-search-mode` | `grok_search_mode` | `web_search`、`x_search`、`both` | `web_search` |

<details>
<summary><strong>从 GitHub 安装最新开发版本</strong></summary>

```bash
pipx install 'git+https://github.com/JerryLiu369/agent-web-search.git'
```

</details>

> [!IMPORTANT]
> 不要把 API Key 写入 Shell 历史、源代码、Git 提交、截图或纳入版本控制的
> MCP 配置。请通过服务端或本地环境变量提供 Key。

## 统一请求与响应

MCP 对外注册一个名为 `web_search` 的工具；CLI 映射到同一组输入。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `query` | string | 是 | — | 完整的自然语言搜索问题 |
| `max_results` | integer，1–20 | 否 | `10` | 期望返回的最大结果数量 |
| `max_keyword` | integer，1–10 | 否 | `3` | 期望使用的最大搜索查询词或关键词数量 |
| `time_range` | `d`、`w`、`m`、`y` | 否 | — | 过去一天、一周、一月或一年 |
| `providers` | string 数组 | 否 | 所有已启用 Provider | 将本次请求限制在指定的已启用 Provider 中 |
| `grok_search_mode` | `web_search`、`x_search`、`both` | 否 | `web_search` | 仅在启用 Grok 时可用 |

调用示例：

```json
{
  "query": "过去一个月发布的 GPU kernel generation 论文",
  "max_results": 5,
  "time_range": "m",
  "providers": ["ddgs", "exa"]
}
```

Provider 选择分为两层：

1. `AGENT_WEB_SEARCH_PROVIDERS` 决定进程启动时启用哪些 Provider。
2. 请求级 `providers` 参数可以进一步缩小范围，但不能启用启动时未启用的 Provider。

### 响应格式

每个成功返回的 Provider 会出现在 `providers` 字段中；失败的 Provider 会被剔除：

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

| 字段 | 含义 |
| --- | --- |
| `answer` | 后端生成时返回的文本回答，无则省略该字段 |
| `results` | 结果行：`title`、`url`、`description`，以及可选的 `published_at` 和 `author` |

如果选中的 Provider 全部失败，MCP 会返回工具错误；CLI 则把同一载荷写入
stderr 并以状态码 1 退出。两者都使用稳定错误码 `all_providers_failed`，并附带
各 Provider 的诊断信息：

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

CLI、MCP 服务器和 Hermes 插件都是 `agent_web_search.SearchEngine` 的薄封装，后者即公开的 Python API。`SearchRequest` 接受与 MCP 工具参数相同的字段：

```python
from agent_web_search import SearchEngine, SearchRequest

engine = SearchEngine()  # 构造时读取 AGENT_WEB_SEARCH_* 环境变量

response = engine.search(
    SearchRequest(query="MCP 规范最近的变化", max_results=5, time_range="m")
)

for name, provider in response.providers.items():
    print(f"{name}: searched={provider.searched}, results={len(provider.results)}")

if response.all_providers_failed:
    print(response.failed_provider_errors)
```

## 配置

CLI、MCP 服务器或 Hermes 插件启动时会读取环境变量。修改 Provider 设置后需要重启对应进程。仓库内的 [`.env.example`](.env.example) 以注释模板的形式列出了全部变量。

### 通用设置

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `AGENT_WEB_SEARCH_PROVIDERS` | `ddgs,exa,parallel` | 以逗号分隔的启动时启用 Provider 列表 |
| `AGENT_WEB_SEARCH_TIMEOUT` | `60` | 单次上游 HTTP 调用的 socket 超时。多步 Provider 会成倍放大：keyless Parallel 最多发 3 个请求（最坏 3×），ARK 可能追加续写请求（最坏 2×），因此整次搜索最长可达该值的 3 倍 |

示例：

```bash
export AGENT_WEB_SEARCH_PROVIDERS="ddgs,exa,brave"
export AGENT_WEB_SEARCH_TIMEOUT="30"
```

```powershell
$env:AGENT_WEB_SEARCH_PROVIDERS = "ddgs,exa,brave"
$env:AGENT_WEB_SEARCH_TIMEOUT = "30"
```

### HTTP Transport 设置

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `AGENT_WEB_SEARCH_MCP_TRANSPORT` | `stdio` | 可选 `stdio` 或 `http`；`--transport` 可以覆盖它 |
| `AGENT_WEB_SEARCH_HTTP_HOST` | `0.0.0.0` | 容器部署时的 HTTP 监听地址 |
| `AGENT_WEB_SEARCH_HTTP_PORT` | `PORT` 或 `8000` | HTTP 监听端口；显式值优先于平台 `PORT` |
| `AGENT_WEB_SEARCH_AUTH_TOKEN` | — | HTTP 必需的 Bearer Token，至少 32 个字符 |
| `AGENT_WEB_SEARCH_ALLOW_ANONYMOUS` | `false` | 为可信网络或临时 Demo 显式关闭 HTTP 鉴权 |
| `AGENT_WEB_SEARCH_HTTP_ALLOWED_HOSTS` | — | 可选、逗号分隔的 Host 白名单 |
| `AGENT_WEB_SEARCH_HTTP_ALLOWED_ORIGINS` | — | 可选、逗号分隔的 Origin 白名单；必须同时配置 Host |
| `AGENT_WEB_SEARCH_HTTP_LOG_LEVEL` | `info` | 容器服务器的 Uvicorn 日志级别 |

HTTP 设置仍然全部来自环境变量；部署文件不会引入第二套应用配置格式。

### Provider 设置

下面先列出默认 Provider，其余可选 Provider 按字母顺序排列。

#### 1. DDGS

DDGS 使用 DuckDuckGo，不需要 API Key 或 Provider 专用环境变量。包安装时会自动安装 `ddgs` Python 依赖。

#### 2. Exa

Exa 同时支持付费和免 Key 模式。

| 变量 | 必填 | 用途 |
| --- | :---: | --- |
| `EXA_API_KEY` | 否 | 设置后使用付费 Search API |
| `EXA_MCP_URL` | 否 | 未设置 API Key 时覆盖默认免费 MCP 地址 |

未设置 `EXA_API_KEY` 时，Exa 会尽力通过免费 MCP 端点搜索。付费 API 通常具有更高的配额和可靠性。

#### 3. Parallel

Parallel 返回适合放入 LLM 上下文的信息密集型摘录。统一的 `parallel` Provider 会自动选择传输方式：

- 未设置 Key 时，使用 Parallel 免费 Search MCP。
- 设置 `PARALLEL_API_KEY` 后，使用付费 Search REST API。

两种方式都会把 `excerpts` 映射到统一结果的 description 字段，调用 Agent 无需区分 `parallel-free` 和 `parallel`。

| 变量 | 必填 | 用途 |
| --- | :---: | --- |
| `PARALLEL_API_KEY` | 否 | 启用付费 API；省略时使用免费 MCP |

Parallel 默认启用，Key 为可选项。

#### 4. ARK（推荐）

火山引擎 ARK 通过 Responses API 提供模型驱动的联网搜索。配置 Key 后，将 `ark` 加入 `AGENT_WEB_SEARCH_PROVIDERS`。

| 变量 | 必填 | 用途 |
| --- | :---: | --- |
| `ARK_API_KEY` | 是 | 单个 Key，或用逗号/换行分隔的多个 Key |
| `AGENT_WEB_SEARCH_ARK_MODELS` | 否 | 用逗号/换行分隔的 ARK 模型 ID |

只配置一个模型时会固定使用该模型；配置多个模型时，连续请求会轮询选择模型。配置多个 ARK Key 时，每次请求会选择一个 Key。

<details>
<summary><strong>可选的火山引擎协作奖励计划信息</strong></summary>

使用 Agent Web Search 不要求参加奖励计划。ARK 用户可以自行查看官方的[火山引擎协作奖励计划](https://www.volcengine.com/docs/82379/1391869?lang=zh)。配额、支持模型、有效期和数据授权条款可能变化，请在选择加入前查看官方最新条款。参与计划并不是使用 Agent Web Search 的前提。

</details>

#### 5. Brave

| 变量 | 必填 | 用途 |
| --- | :---: | --- |
| `BRAVE_SEARCH_API_KEY` | 是 | Brave Web Search API 凭据 |

配置 Key 后，将 `brave` 加入 `AGENT_WEB_SEARCH_PROVIDERS`。

#### 6. Gemini

| 变量 | 必填 | 用途 |
| --- | :---: | --- |
| `GEMINI_API_KEY` | 是 | Google AI API 凭据 |
| `AGENT_WEB_SEARCH_GEMINI_MODELS` | 否 | 用逗号/换行分隔的 Gemini 模型 ID |

Gemini 会把通用的结果数量和时间控制尽力转换为 Prompt 约束。只配置一个模型时固定使用该模型；配置多个模型时连续请求会轮询选择模型。

#### 7. Grok

| 变量 | 必填 | 用途 |
| --- | :---: | --- |
| `XAI_API_KEY` | 是 | xAI API 凭据 |
| `AGENT_WEB_SEARCH_GROK_MODELS` | 否 | 用逗号/换行分隔的 Grok 模型 ID |

只配置一个模型时固定使用该模型；配置多个模型时连续请求会轮询选择模型。

启用 Grok 后，公开工具 Schema 会增加 `grok_search_mode`：

- `web_search` 搜索网页。
- `x_search` 搜索 X，并在可用时采用原生日期过滤器。
- `both` 在一次请求中同时向服务端暴露这两种工具并让 Grok 选择；它不会发起两个独立的模型请求。

#### 8. Perplexity

该 Provider 使用 Perplexity 原生的结构化 Search API，返回搜索结果行，而不是由 Sonar 生成的文本回答。该 Provider 不包含 OpenRouter 兼容逻辑。

| 变量 | 必填 | 用途 |
| --- | :---: | --- |
| `PERPLEXITY_API_KEY` | 是 | Perplexity Search API 凭据 |

配置 Key 后，将 `perplexity` 加入 `AGENT_WEB_SEARCH_PROVIDERS`。

#### 9. Tavily

| 变量 | 必填 | 用途 |
| --- | :---: | --- |
| `TAVILY_API_KEY` | 是 | Tavily Search API 凭据 |

配置 Key 后，将 `tavily` 加入 `AGENT_WEB_SEARCH_PROVIDERS`。

#### 10. You.com

You.com 返回统一的网页和新闻结果。Agent Web Search 会合并两部分、按 URL 去重，并将 `max_results` 应用于合并后的结果列表。

| 变量 | 必填 | 用途 |
| --- | :---: | --- |
| `YDC_API_KEY` | 是 | You.com Search API 凭据 |

配置 Key 后，将 `you` 加入 `AGENT_WEB_SEARCH_PROVIDERS`。

### 通用搜索控制

每个 Provider 会尽可能将公共控制参数映射到原生 API，不支持的参数会被忽略。

| Provider | `max_results` | `max_keyword` | `time_range` |
| --- | --- | --- | --- |
| DDGS | 原生 `max_results` | 忽略 | 原生 `timelimit` |
| Exa | 原生结果数量 | 忽略 | 原生发布日期 |
| Parallel | REST：原生 `max_results`；keyless MCP：客户端截断（`results[:max_results]`） | 忽略 | 忽略 |
| ARK | 原生 `limit` | 原生支持 | Prompt 约束 |
| Brave | 原生 `count` | 忽略 | 原生 `freshness` |
| Gemini | Prompt 约束 | Prompt 约束 | Prompt 约束 |
| Grok | Prompt 约束 | Prompt 约束 | Prompt；X Search 还会使用原生日期参数 |
| Perplexity | 原生 `max_results` | 忽略 | 原生时间范围过滤 |
| Tavily | 原生 `max_results` | 忽略 | 原生 `time_range` |
| You.com | 原生 `count`，合并后截断 | 忽略 | 原生 `freshness` |

基于 Prompt 的控制属于尽力而为，不是严格保证。

## 其他接口

### Hermes 原生插件

直接从 GitHub 安装原生插件：

```bash
pip install 'ddgs>=9.0'
hermes plugins install JerryLiu369/agent-web-search --no-enable
hermes plugins enable agent-web-search --allow-tool-override
```

该插件会有意替换 Hermes 内置的 `web_search` 工具，因此必须显式授予 `--allow-tool-override` 权限。启用后请启动新的 Hermes 会话；通过消息渠道使用时还需要重启 gateway。

Hermes 也可以不安装原生插件，而是通过通用 MCP 集成连接本项目。

## 故障排查

- **`all_providers_failed`** —— 所有 Provider 都失败了。MCP 会标记工具错误；CLI 会把诊断写入 stderr 并退出 1。请检查 Key、配额和网络；临时限流可以有界重试一次。
- **找不到 `agent-web-search`** —— 使用 `pipx` 或 `pip` 安装 PyPI 包，然后重新打开 Shell，确保脚本目录已经加入 `PATH`。
- **HTTP 401 `invalid_token`** —— `Authorization: Bearer …` 请求头必须与 `AGENT_WEB_SEARCH_AUTH_TOKEN` 一致，且该 Token 至少 32 个字符。
- **响应里少了某个 Provider** —— 失败的 Provider 会从成功响应中剔除。Python API 可以通过 `response.failed_provider_errors` 查看原因。
- **修改 Provider 配置不生效** —— Provider 设置只在进程启动时读取一次；修改后请重启 CLI、MCP 服务器或 Hermes 插件。
- **MCP 客户端在工具返回前超时** —— `AGENT_WEB_SEARCH_TIMEOUT` 限定的是单次上游 HTTP 调用的超时，不是整次搜索。keyless Parallel 最多发 3 个请求，ARK 可能追加续写请求，最坏总耗时是其 3 倍；请据此设置 MCP 客户端的 tool 超时。

## 开发

使用 [`uv`](https://docs.astral.sh/uv/) 可以保持开发环境隔离且可复现：

```bash
git clone https://github.com/JerryLiu369/agent-web-search.git
cd agent-web-search
uv venv
uv pip install -e '.[dev]'
uv run pytest -q
uv run ruff check .
```

<details>
<summary><strong>标准 venv + pip 方式</strong></summary>

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
pytest -q
ruff check .
```

</details>

[ARCHITECTURE.md](ARCHITECTURE.md) 是设计事实来源，[AGENTS.md](AGENTS.md) 列出了不可妥协的约束。在修改 Transport、配置、鉴权、部署、Provider 或工具 Schema 之前，请先阅读这两份文档，保持 stdio 与 HTTP 行为一致，并在同一改动中保持 `pytest` 和 `ruff` 通过。

## 许可证

[MIT](LICENSE)
