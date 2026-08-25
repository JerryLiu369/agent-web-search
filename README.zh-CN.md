<div align="center">

# Agent Web Search

**面向 AI Agent 的统一联网搜索工具，由多个相互独立的 Provider 提供支持。**

[English](https://github.com/JerryLiu369/agent-web-search/blob/main/README.md) | **简体中文**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/agent-web-search-mcp.svg)](https://pypi.org/project/agent-web-search-mcp/)
[![CI](https://github.com/JerryLiu369/agent-web-search/actions/workflows/ci.yml/badge.svg)](https://github.com/JerryLiu369/agent-web-search/actions/workflows/ci.yml)
[![MCP 2.x](https://img.shields.io/badge/MCP-2.x-6C47FF)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

支持 **Codex CLI**、**Claude Code**、**OpenCode**、**Hermes**、普通命令行脚本、Python 应用和远程 Streamable HTTP MCP 客户端。

[搜索服务](#搜索服务) · [快速开始](#快速开始) ·
[远程 MCP](#通过-https-使用远程-mcp) ·
[工具接口](#工具接口) · [配置](#配置) ·
[集成](#集成) · [架构](ARCHITECTURE.md) · [开发](#开发)

</div>

---

Agent Web Search 对外提供一个与 Provider 无关的 `web_search` 工具。它会并发调用彼此独立的 Provider，统一不同返回格式，隔离单个 Provider 的故障，并允许调用 Agent 在每次请求中选择要使用的已启用 Provider。

```text
Agent / MCP 客户端
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

## 快速开始

选择你已经使用的 Python 包管理方式，从 PyPI 安装：

```bash
# 标准 Python 安装
python -m pip install agent-web-search-mcp

# 隔离且持久的安装
pipx install agent-web-search-mcp

# 无需持久安装，直接运行
uvx agent-web-search-mcp
```

`pip` 和 `pipx` 会安装下面两个命令；`uvx` 则会直接运行调用中指定的命令。

持久安装后，无需配置付费 API Key 即可搜索：

```bash
agent-web-search "OpenAI Codex CLI 最新版本有哪些变化？"
```

也可以不安装，通过 `uvx` 直接运行 CLI：

```bash
uvx --from agent-web-search-mcp agent-web-search \
  "OpenAI Codex CLI 最新版本有哪些变化？"
```

或者启动供 MCP 客户端连接的 stdio 服务器：

```bash
agent-web-search-mcp
```

如果希望 MCP 客户端直接通过 `uvx` 运行而不预先安装，可以让客户端执行 `uvx agent-web-search-mcp`。例如：

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
<summary><strong>从 GitHub 安装最新开发版本</strong></summary>

```bash
pipx install 'git+https://github.com/JerryLiu369/agent-web-search.git'
```

</details>

> [!IMPORTANT]
> 不要把 API Key 写入 Shell 历史、源代码、Git 提交、截图或纳入版本控制的 MCP 配置。请通过密钥管理工具或未提交到仓库的本地环境变量文件提供密钥。

## 通过 HTTPS 使用远程 MCP

同一个 `agent-web-search-mcp` 命令同时支持两种 MCP Transport。无参数时保持 stdio，通过 Transport 参数启动无状态 Streamable HTTP：

```bash
# 只需生成一次部署 Token
python -c "import secrets; print(secrets.token_urlsafe(32))"

export AGENT_WEB_SEARCH_AUTH_TOKEN="替换为刚生成的-token"
agent-web-search-mcp --transport http
```

HTTP 服务提供 `POST /mcp` 和公开的 `GET /healthz`。`/mcp` 默认强制验证部署 Bearer Token，并且不会创建 `MCP-Session-Id`。

远程 MCP 客户端配置示例：

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

### 一键部署

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FJerryLiu369%2Fagent-web-search&env=AGENT_WEB_SEARCH_AUTH_TOKEN)
[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/new/template?template=https%3A%2F%2Fgithub.com%2FJerryLiu369%2Fagent-web-search&envs=AGENT_WEB_SEARCH_AUTH_TOKEN)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/JerryLiu369/agent-web-search)

所有公网部署都必须把 `AGENT_WEB_SEARCH_AUTH_TOKEN` 设置为至少 32 个字符。Provider Key 继续作为可选的服务端环境变量。

Zeabur 可以使用仓库内的 `Dockerfile` 直接从 Git 部署。Zeabur 必须先在平台账号中发布 Template，才能生成可复用的一键部署按钮；完成这次账号侧发布后再补上按钮。

通用 Docker 部署：

```bash
docker build -t agent-web-search .
docker run --rm -p 8000:8000 \
  -e AGENT_WEB_SEARCH_AUTH_TOKEN="替换为至少-32-字符的-token" \
  agent-web-search
```

## 工具接口

MCP 服务器和 Hermes 插件都会注册一个名为 `web_search` 的工具。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `query` | string | 是 | — | 完整的自然语言搜索问题 |
| `max_results` | integer，1–20 | 否 | `10` | 期望返回的结果或引用数量 |
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

单个 Provider 失败时，它会从成功结果中剔除。如果选中的 Provider 全部失败，MCP 会返回工具错误，稳定错误码为 `all_providers_failed`，并附带各 Provider 的诊断信息。

## 配置

CLI、MCP 服务器或 Hermes 插件启动时会读取环境变量。修改 Provider 设置后需要重启对应进程。

### 通用设置

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `AGENT_WEB_SEARCH_PROVIDERS` | `ddgs,exa,parallel` | 以逗号分隔的启动时启用 Provider 列表 |
| `AGENT_WEB_SEARCH_TIMEOUT` | `60` | 单个 Provider 的超时时间，单位为秒 |

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
| Parallel | 原生 `max_results` | 忽略 | 忽略 |
| ARK | 原生 `limit` | 原生支持 | Prompt 约束 |
| Brave | 原生 `count` | 忽略 | 原生 `freshness` |
| Gemini | Prompt 约束 | Prompt 约束 | Prompt 约束 |
| Grok | Prompt 约束 | Prompt 约束 | Prompt；X Search 还会使用原生日期参数 |
| Perplexity | 原生 `max_results` | 忽略 | 原生时间范围过滤 |
| Tavily | 原生 `max_results` | 忽略 | 原生 `time_range` |
| You.com | 原生 `count`，合并后截断 | 忽略 | 原生 `freshness` |

基于 Prompt 的控制属于尽力而为，不是严格保证。

## 集成

### Codex CLI

```bash
codex mcp add agent-web-search -- agent-web-search-mcp
codex mcp list
```

### Claude Code

```bash
claude mcp add agent-web-search -- agent-web-search-mcp
```

也可以添加项目级 `.mcp.json`：

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

直接从 GitHub 安装原生插件：

```bash
pip install 'ddgs>=9.0'
hermes plugins install JerryLiu369/agent-web-search --no-enable
hermes plugins enable agent-web-search --allow-tool-override
```

该插件会有意替换 Hermes 内置的 `web_search` 工具，因此必须显式授予 `--allow-tool-override` 权限。启用后请启动新的 Hermes 会话；通过消息渠道使用时还需要重启 gateway。

Hermes 也可以不安装原生插件，而是通过通用 MCP 集成连接本项目。

## CLI 示例

```bash
# 使用所有启动时启用的 Provider
agent-web-search "OpenAI Codex CLI 最新版本有哪些变化？"

# 限制结果数量和发布时间
agent-web-search "GPU kernel generation 论文" --time-range m --max-results 5

# 只选择部分 Provider
agent-web-search "最新 AI 新闻" --provider ark --provider ddgs
```

## 设计原则

- **一个核心，多种适配。** MCP、Hermes、CLI 和 Python 使用同一个搜索引擎和响应模型。
- **Provider 相互独立。** 单个 Provider 失败不会丢弃其他 Provider 的成功结果；全部失败时会明确返回错误。
- **执行过程透明。** 响应会暴露 `searched` 和 `model`，不会把每一个 HTTP 200 都视为已完成搜索。
- **不共享密钥。** 项目不包含遥测，也不提供共享 API Key 服务。

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

## 许可证

[MIT](LICENSE)
