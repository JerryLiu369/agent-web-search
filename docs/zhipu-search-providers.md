# 智谱三种搜索协议与 Provider 设计

> 研究日期：2026-09-03
>
> 本文只覆盖三种能力：独立 Web Search API、Chat API 内置 Web Search、Coding Plan 搜索 MCP。本文记录的是官方协议资料和插件适配建议，不代表任意第三方 GLM 兼容网关都实现了这些能力。

## 结论

建议在 `agent-web-search` 中做成三个独立 Provider，不要把三种协议塞进一个“GLM Provider”里：

1. `zhipu_web_search`：独立 Web Search API，直接返回结构化搜索结果。
2. `zhipu_chat_search`：Chat Completions 内置 `web_search`，返回模型回答，可选返回搜索结果。
3. `zhipu_search_mcp`：Coding Plan Remote MCP，通过 `tools/list` 和 `tools/call` 使用 `webSearchPrime`。

三者可以共享最终的结果标准化函数，但必须分别保留请求构造、鉴权、错误处理和响应解析。独立 API 是“搜索结果接口”，Chat 是“搜索加模型回答接口”，MCP 是“工具发现与调用协议”；它们不是同一个 API 的三种写法。[11]

## 1. 独立 Web Search API

### 1.1 端点和鉴权

中国区端点：

```http
POST https://open.bigmodel.cn/api/paas/v4/web_search
Authorization: Bearer <ZHIPU_API_KEY>
Content-Type: application/json
```

这是一次普通的 JSON 请求，当前公开资料没有把它定义成流式接口。插件应把它当作结构化检索 Provider，而不是模型对话 Provider。[5]

### 1.2 请求体

```json
{
  "search_query": "GLM-5.3-Flash 最新消息",
  "search_engine": "search_pro",
  "search_intent": false,
  "count": 10,
  "search_domain_filter": "docs.bigmodel.cn",
  "search_recency_filter": "noLimit",
  "content_size": "medium",
  "request_id": "req_123456",
  "user_id": "user_123456"
}
```

字段：

| 字段 | 类型 | 必填/默认 | 说明 |
| --- | --- | --- | --- |
| `search_query` | string | 必填 | 搜索词；中国区 OpenAPI 最大长度为 70 |
| `search_engine` | string | 必填 | 中国区资料出现 `search_std`、`search_pro`、`search_pro_sogou`、`search_pro_quark` |
| `search_intent` | boolean | 当前 OpenAPI 必填；文档默认 `false` | 是否先做搜索意图识别 |
| `count` | integer | 可选；默认 10 | 范围 1–50 |
| `search_domain_filter` | string | 可选 | 域名过滤/白名单 |
| `search_recency_filter` | string | 可选 | `oneDay`、`oneWeek`、`oneMonth`、`oneYear`、`noLimit` |
| `content_size` | string | 可选 | `medium` 或 `high` |
| `request_id` | string | 可选 | 6–64 个字符 |
| `user_id` | string | 可选 | 6–128 个字符 |

`search_intent` 可能返回以下意图：

```text
SEARCH_ALL
SEARCH_NONE
SEARCH_ALWAYS
```

当前中国区 OpenAPI 将 `search_intent` 标为必填，但部分官方示例没有传它。新 Provider 应显式发送 `false`，不要依赖服务端默认值。[5]

### 1.3 响应体

```json
{
  "id": "task-id",
  "created": 1748261757,
  "request_id": "req_123456",
  "search_intent": [
    {
      "query": "GLM-5.3-Flash 最新消息",
      "intent": "SEARCH_ALL",
      "keywords": "GLM-5.3-Flash 最新消息"
    }
  ],
  "search_result": [
    {
      "title": "网页标题",
      "content": "网页摘要",
      "link": "https://example.com/article",
      "media": "Example",
      "icon": "https://example.com/favicon.ico",
      "refer": "ref_1",
      "publish_date": "2026-08-20"
    }
  ]
}
```

核心结果数组是：

```text
response.search_result[]
```

结果项字段：

```text
title         网页标题
content       网页摘要或正文片段
link          网页 URL
media         网站/媒体名称
icon          网站图标 URL
refer         引用标识，例如 ref_1
publish_date  发布时间
```

映射到项目公共结果：

```text
title        → SearchResult.title
link         → SearchResult.url
content      → SearchResult.description
publish_date → SearchResult.published_at
```

`media`、`icon`、`refer` 可以留在 Provider 内部解析结果中，但当前项目公共 `SearchResult` 没有对应字段，不应为了保留它们而改变公共响应协议。

### 1.4 错误

```json
{
  "error": {
    "code": "1701",
    "message": "网络搜索并发已达上限"
  }
}
```

已知搜索相关错误码：

```text
1701  网络搜索并发达到上限
1702  没有可用搜索引擎
1703  搜索引擎没有返回有效数据
```

Provider 不应把上游完整响应体或异常字符串直接放入公共错误，避免泄露凭据和内部信息。应把 HTTP 状态、错误类别和必要的稳定错误码映射到现有 Provider 错误机制。

### 1.5 海外端点不能直接混用

Z.AI 海外端点是：

```http
POST https://api.z.ai/api/paas/v4/web_search
```

当前资料中它使用的搜索引擎编码是：海外 Z.AI 指南示例中的 `search-prime`；海外 API schema 中还定义了 `search_pro_jina`。这与中国区示例中的 `search_pro` 不同，请以目标端点的实际 schema 为准。请求字段集合也不完全相同。因此端点、搜索引擎和字段集合必须作为 Provider 配置，不要写成全局常量。[10]

## 2. Chat API 内置 Web Search

### 2.1 端点

```http
POST https://open.bigmodel.cn/api/paas/v4/chat/completions
Authorization: Bearer <ZHIPU_API_KEY>
Content-Type: application/json
```

这是 Chat Completions 请求，只是在 `tools` 中加入智谱原生的 `web_search` 工具。它的主要产品输出是模型回答，不是独立搜索结果。[11][12]

### 2.2 请求体

```json
{
  "model": "glm-4-air",
  "messages": [
    {
      "role": "user",
      "content": "总结 GLM-5.3-Flash 的最新信息"
    }
  ],
  "tools": [
    {
      "type": "web_search",
      "web_search": {
        "enable": true,
        "search_engine": "search_pro",
        "search_query": "GLM-5.3-Flash 最新信息",
        "count": 5,
        "search_domain_filter": "docs.bigmodel.cn",
        "search_recency_filter": "noLimit",
        "content_size": "high",
        "result_sequence": "after",
        "search_result": true,
        "require_search": true,
        "search_prompt": "根据搜索结果生成简洁摘要并引用来源。"
      }
    }
  ]
}
```

工具外层必须是：

```json
{
  "type": "web_search",
  "web_search": {
    "enable": true
  }
}
```

它不是普通的 OpenAI 函数工具，也不能省略 `web_search` 嵌套对象。

### 2.3 `web_search` 字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `enable` | boolean | 是否启用联网搜索，当前 OpenAPI 默认 `false` |
| `search_engine` | string | 中国区资料示例使用 `search_pro`；海外 Z.AI 指南示例使用 `search-prime`，其当前 Chat OpenAPI schema 定义为 `search_pro_jina` |
| `search_query` | string | 强制指定搜索词 |
| `count` | integer | 结果数量，1–50，默认 10 |
| `search_domain_filter` | string | 域名过滤 |
| `search_recency_filter` | string | `oneDay`、`oneWeek`、`oneMonth`、`oneYear`、`noLimit` |
| `content_size` | string | `medium` 或 `high` |
| `result_sequence` | string | `before` 或 `after`，控制搜索结果放入模型上下文的位置 |
| `search_result` | boolean | 是否在响应中返回原始搜索结果 |
| `require_search` | boolean | 是否强制模型基于搜索结果回答 |
| `search_prompt` | string | 指定模型如何处理搜索结果 |

官方旧示例中有字符串形式：

```json
{
  "enable": "True",
  "count": "5",
  "search_result": "True"
}
```

当前 OpenAPI 和 Java SDK 使用 JSON 原生类型：

```json
{
  "enable": true,
  "count": 5,
  "search_result": true
}
```

新 Provider 默认应使用 boolean/integer。若要兼容旧代理，应增加明确的兼容模式，不要在所有请求中无条件把值转换成字符串。[12][14][15]

### 2.4 非流式响应

```json
{
  "id": "response-id",
  "created": 1748311718,
  "model": "glm-4-air",
  "request_id": "response-id",
  "choices": [
    {
      "index": 0,
      "finish_reason": "stop",
      "message": {
        "role": "assistant",
        "content": "根据搜索结果，GLM-5.3-Flash 的最新信息包括……[来源：ref_1]"
      }
    }
  ],
  "usage": {
    "prompt_tokens": 4199,
    "completion_tokens": 868,
    "total_tokens": 5067
  },
  "web_search": [
    {
      "title": "网页标题",
      "content": "网页摘要",
      "link": "https://example.com/article",
      "media": "Example",
      "icon": "https://example.com/favicon.ico",
      "refer": "ref_1",
      "publish_date": "2026-08-20"
    }
  ]
}
```

插件应分别解析两层：

```text
answer  = response.choices[].message.content
results = response.web_search[]（仅在 search_result=true 且服务端返回时存在）
```

`answer` 是模型生成的文本，可能引用 `ref_1` 等标记。不能只从回答正文中用正则抓 URL；如果顶层 `web_search` 存在，应优先使用其中的结构化结果。

Chat Provider 合法的结果形态包括：

```text
answer 非空，results 非空
answer 非空，results 为空
answer 为空，results 非空（少见，但解析器应允许）
```

不要因为没有结构化结果，就把模型回答判定为失败。

### 2.5 流式响应

官方 SDK 类型还描述了搜索相关的工具调用结构。非流式时可能出现在：

```text
choices[].message.tool_calls[]
```

流式时可能出现在：

```text
choices[].delta.tool_calls[]
```

搜索相关块可能包含：

```json
{
  "index": 0,
  "type": "web_search",
  "search_intent": {
    "index": 0,
    "query": "...",
    "intent": "SEARCH_ALL",
    "keywords": "..."
  },
  "search_result": {
    "index": 0,
    "title": "网页标题",
    "link": "https://example.com",
    "content": "网页摘要",
    "refer": "ref_1"
  },
  "search_recommend": {
    "index": 0,
    "query": "推荐的后续查询"
  }
}
```

因此流式解析不能只拼接 `delta.content`。但不同网关可能省略部分事件类型，解析器应忽略未知字段而不是拒绝整条响应。[15]

## 3. Coding Plan 搜索 MCP

### 3.1 端点和工具

中国区当前文档给出的 Remote MCP 端点：

```text
https://open.bigmodel.cn/api/mcp/web_search_prime/mcp
```

核心工具名：

```text
webSearchPrime
```

鉴权仍通过 HTTP Header：

```http
Authorization: Bearer <CODING_PLAN_API_KEY>
```

它仍然是 MCP 服务，不是 `/api/paas/v4/web_search`，也不是 `/api/paas/v4/chat/completions`。官方 MCP 页面公开了工具用途和工具名，但没有把完整 `inputSchema` 固定写成 REST API 那种稳定请求表。中国区当前使用 `open.bigmodel.cn`；海外 Z.AI 当前也提供对应的 `/api/mcp/web_search_prime/mcp` Streamable HTTP 端点，部分旧客户端仍可使用 `/sse` 兼容配置。端点必须作为 Provider 配置，而不是写死在结果解析器中。[3][9]

### 3.2 生命周期

Provider 内部应完成标准 MCP 顺序：

```text
initialize
→ notifications/initialized
→ tools/list
→ tools/call
```

`initialize` 示例：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {
      "name": "agent-web-search",
      "version": "0.1.0"
    }
  }
}
```

实际客户端应进行协议版本协商，不要把示例版本当成服务端永远固定的版本。

初始化后发送通知：

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

### 3.3 `tools/list`

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

服务端会返回工具定义，例如：

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "webSearchPrime",
        "description": "搜索网络信息",
        "inputSchema": {
          "type": "object",
          "properties": {
            "search_query": {
              "type": "string"
            }
          },
          "required": ["search_query"]
        }
      }
    ]
  }
}
```

Provider 必须检查：

```text
是否找到 webSearchPrime
inputSchema 的 required 字段
inputSchema 的属性名、类型和枚举
```

不要因为公开资料中出现了 `search_query`、`count` 等字段，就不经 `tools/list` 直接硬编码全部参数。

### 3.4 `tools/call`

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "webSearchPrime",
    "arguments": {
      "search_query": "GLM-5.3-Flash 最新消息"
    }
  }
}
```

公开客户端实现中还出现过以下兼容参数：

```json
{
  "search_query": "GLM-5.3-Flash 最新消息",
  "count": 10,
  "content_size": "medium",
  "location": "cn",
  "search_domain_filter": "docs.bigmodel.cn",
  "search_recency_filter": "noLimit"
}
```

这些字段只能在服务端 `inputSchema` 允许时发送。MCP Provider 的参数构造逻辑应当是：

```text
读取 tools/list
→ 根据 inputSchema 过滤/构造 arguments
→ 调用 webSearchPrime
```

而不是：

```text
把独立 Web Search API 的请求体原样塞进 MCP
```

### 3.5 MCP 响应

标准工具调用结果：

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "[{\"title\":\"网页标题\",\"link\":\"https://example.com\",\"content\":\"网页摘要\"}]"
      }
    ],
    "isError": false
  }
}
```

解析顺序：

```text
JSON-RPC response
→ result
→ content[]
→ 找到 type=text 的 block
→ 对 text 尝试 JSON 解码
→ 提取数组或 items/results/data 下的结果
→ 映射为 SearchResult
```

兼容解析器至少应支持以下包装：

```json
[
  {"title": "...", "link": "...", "content": "..."}
]
```

```json
{
  "items": [
    {"title": "...", "url": "...", "summary": "..."}
  ]
}
```

```json
{
  "results": [
    {"title": "...", "link": "...", "content": "..."}
  ]
}
```

字段归一化：

```text
title                  → SearchResult.title
link 或 url            → SearchResult.url
content 或 summary     → SearchResult.description
publish_date 或 date  → SearchResult.published_at
```

如果返回：

```json
"isError": true
```

必须记为 Provider 失败，不得当成“搜索成功但没有结果”。MCP 原始 `content` block 可以留在 Provider 内部诊断对象中，但不要直接暴露到项目公共响应。

## 4. 三个 Provider 的边界

### 4.1 可以共享的部分

三个 Provider 都可以复用现有 Provider 接口：

```python
class Provider(ABC):
    def search(self, request: SearchRequest) -> ProviderResponse: ...
```

也可以共享：

- `SearchRequest` 的 `query`、`max_results`、`time_range`；
- 超时和基础 HTTP 工具；
- URL 去重；
- `SearchResult` 标准化；
- `ProviderResponse(answer, results, model, ...)`；
- 错误脱敏和 Provider 失败汇总。

### 4.2 不应共享的部分

以下部分必须各自实现：

```text
请求端点
Authorization 形式及凭据配置
请求 JSON 结构
搜索参数映射
HTTP/JSON-RPC 生命周期
错误 envelope
流式事件解析
响应结果解包
```

尤其不能做成一个解析器：

```python
if provider == "zhipu":
    # 根据返回字段猜是 REST、Chat 还是 MCP
```

这样会把三种不兼容协议的分支混在一起，后续遇到字段冲突时很难判断是哪个协议的问题。

## 5. Provider 命名和配置建议

建议名称直接表达协议，不要只叫 `glm`：

```text
zhipu_web_search   独立结构化 Web Search API
zhipu_chat_search  Chat API + web_search 工具
zhipu_search_mcp   Coding Plan Search MCP
```

建议每个 Provider 都支持独立的端点配置和凭据配置：

```text
ZHIPU_WEB_SEARCH_URL
ZHIPU_WEB_SEARCH_API_KEY

ZHIPU_CHAT_SEARCH_URL
ZHIPU_CHAT_SEARCH_API_KEY
ZHIPU_CHAT_SEARCH_MODEL

ZHIPU_SEARCH_MCP_URL
ZHIPU_SEARCH_MCP_API_KEY
```

即使三者实际可以使用同一个智谱账号，也不要在代码层面默认共用一套配置。这样可以单独替换中国区/海外端点，也能明确区分普通 API 额度和 Coding Plan 凭据。

## 6. 与现有公共响应的映射

现有项目公共结果契约是：

```json
{
  "query": "...",
  "providers": {
    "zhipu_web_search": {
      "results": [
        {
          "title": "网页标题",
          "url": "https://example.com",
          "description": "网页摘要",
          "published_at": "2026-08-20"
        }
      ]
    },
    "zhipu_chat_search": {
      "answer": "模型根据搜索结果生成的回答……",
      "results": []
    },
    "zhipu_search_mcp": {
      "results": []
    }
  }
}
```

三个 Provider 不需要强行输出相同内容：

- `zhipu_web_search` 主要输出 `results`；
- `zhipu_chat_search` 主要输出 `answer`，结构化结果可能为空；
- `zhipu_search_mcp` 主要输出 `results`，通常没有模型回答。

这比把 Chat 的回答伪装成搜索摘要，或者把 MCP 的文本包装假设成 REST `search_result[]` 更可靠。

## 7. 推荐实现顺序

### 第一阶段：三个 Provider 都先建立边界

先写各自的请求/响应 fixture 和最小实现，保证：

```text
zhipu_web_search 只解析 search_result[]
zhipu_chat_search 只解析 Chat response + 可选 web_search[]
zhipu_search_mcp 只解析 MCP JSON-RPC envelope
```

### 第二阶段：先实现独立 Web Search API

它最适合先落地，因为：

- 请求结构最简单；
- 返回直接是结构化结果；
- 不依赖模型回答质量；
- 最容易映射到现有 `SearchResult`；
- 测试稳定性最高。

### 第三阶段：实现 Chat Web Search

重点覆盖：

- `answer` 存在但 `results` 为空；
- `search_result=true` 时解析顶层结果；
- 引用标识不等于 URL；
- 非流式和流式响应分开测试；
- OpenAPI 原生类型与旧示例字符串类型分开处理。

### 第四阶段：实现 Coding Plan Search MCP

重点覆盖：

- 初始化和协议版本协商；
- `tools/list` 找不到 `webSearchPrime`；
- 动态 `inputSchema`；
- `tools/call` 的 `isError`；
- `content[].text` 的多种 JSON 包装；
- MCP 超时、断开和 JSON-RPC 错误。

## 8. 第三方 GLM 兼容端点的边界

此前对 `https://llmapi.isrc.ac.cn/` 的实测只能确认：

- `/v1/models` 可以发现 `GLM-5.3-Flash`；
- 普通 `/v1/chat/completions` 可以返回对话结果；
- `/v1/responses` 返回 200 不代表真正执行了联网搜索；
- 携带智谱原生 `web_search` 的 Chat 请求返回过 schema 错误；
- `/v1/web_search` 返回 404；
- 因此不能把这个第三方端点当作三种官方搜索协议的验证环境。

实现 Provider 时，应以官方端点和官方协议为目标；第三方代理是否兼容，应单独作为兼容性探测结果记录，不要因为普通 Chat 可用就自动启用三个搜索 Provider。

## 9. 国内版和海外版的差异

### 9.1 独立 Web Search API

**不是完全同一套请求。**

```text
中国区：POST https://open.bigmodel.cn/api/paas/v4/web_search
海外：  POST https://api.z.ai/api/paas/v4/web_search
```

中国区当前资料使用 `search_pro` 等搜索引擎编码，并把 `search_intent` 纳入当前 OpenAPI；海外 Z.AI 当前公开 schema 使用 `search-prime`，字段集合也不完全相同。两边的结果字段仍然高度相似，主要都是 `title`、`content`、`link`、`media`、`icon`、`refer`、`publish_date`。[5][10]

### 9.2 Chat API 内置 Web Search

**协议骨架基本相同，但搜索引擎值和部分版本字段不保证相同。** 两边都是 Chat Completions 加：

```json
{
  "type": "web_search",
  "web_search": {
    "enable": true
  }
}
```

但中国区文档和 OpenAPI 使用 `search_pro`；海外指南示例使用 `search-prime`，而我抓到的海外 Chat OpenAPI schema 定义为 `search_pro_jina`。这说明海外官方资料当前存在示例与 schema 不一致。因此不能只切换域名而保留全部请求值；`search_engine` 应按目标端点的 schema 配置。[11][12][14]

响应语义基本一致：主要回答在 `choices[].message.content`，请求要求返回原始结果时再读取顶层 `web_search`。不过具体模型、可用搜索引擎和流式事件仍应按目标端点实测。[11][14][15]

### 9.3 Coding Plan 搜索 MCP

**工具语义相同，连接配置不完全相同。**

```text
中国区： https://open.bigmodel.cn/api/mcp/web_search_prime/mcp
海外：   https://api.z.ai/api/mcp/web_search_prime/mcp
```

两边都提供 `webSearchPrime`，都应走 MCP 的 `initialize`、`tools/list`、`tools/call`。海外文档还保留了部分旧客户端使用的 SSE 配置；中国区文档也给出了 SSE 兼容配置。MCP Provider 应把 URL、传输类型和凭据作为配置，并在运行时通过 `tools/list` 读取实际 schema。[3][9][16]

**凭据和额度也不要默认混用。** 中国区 Coding Plan 文档明确区分个人/团队 Coding Plan Key，团队套餐 Key 与平台其他 API Key 不通用；海外 MCP 使用 Z.AI 侧的 Coding Plan/API Key。即使两边都采用 Bearer Header，也不代表同一枚 Key 可以跨区或跨产品使用。[3][9]

### 9.4 对 Provider 的直接影响

不要做成一个“国内/海外自动切换”的固定协议 Provider。建议仍然保留三个语义 Provider，但每个 Provider 都允许配置区域端点：

```text
zhipu_web_search  + 中国区或海外 Web Search URL
zhipu_chat_search + 中国区或海外 Chat URL、模型、search_engine
zhipu_search_mcp  + 中国区或海外 MCP URL、传输方式
```

也就是说：**Provider 按能力拆分，区域按配置切换；协议解析不因区域切换而混在一起。** 如果后续发现某一端点的字段或响应确实分叉，再在该 Provider 内增加区域兼容分支，不要把三种能力重新合并。

### 9.5 当前实现范围

第一版只实现中国区 BigModel 端点：

```text
zhipu_web_search  → https://open.bigmodel.cn
zhipu_chat_search → https://open.bigmodel.cn
zhipu_search_mcp  → https://open.bigmodel.cn
```

Z.AI 海外端点（`https://api.z.ai`）当前不纳入实现，也不作为默认 fallback。原因是海外官方资料中的搜索引擎编码存在不一致，且当前没有可用的海外凭据进行三种协议的真实验证。本文保留海外资料仅用于记录差异，不代表插件已经支持该端点。

以后若重新加入 Z.AI，必须先分别验证独立 Web Search API、Chat Web Search 和 Search MCP，再决定是否增加兼容分支。

## 10. 2026-09-03 普通 API Key 实测补充

以下结果来自中国区官方端点的真实请求；凭据不写入本文。测试模型为 `glm-5.3-flash`。

### 10.1 模型和两个搜索面

```text
GET  /api/paas/v4/models                         HTTP 200
模型数量                                         10
目标模型                                         glm-5.3-flash，精确存在
POST /api/paas/v4/web_search                    HTTP 200
POST /api/paas/v4/chat/completions + web_search HTTP 200
```

模型列表中确认存在：

```text
glm-4.5, glm-4.5-air, glm-4.6, glm-4.7, glm-5,
glm-5-turbo, glm-5.1, glm-5.2, glm-5.3, glm-5.3-flash
```

独立 Web Search 返回顶层 `search_result`，结果项实测包含 `content`、`icon`、`link`、`media`、`publish_date`、`refer`、`title`。Chat Web Search 返回非空首个 `choices` 元素的 `message.content`；设置 `search_result=true` 时返回顶层 `web_search[]`，设置为 `false` 时仍返回回答但不返回该数组。

### 10.2 参数映射上的实测约束

- 独立 API 不传 `search_engine` 返回 HTTP 400、错误码 `1214`，错误信息为 `search_engine:The search_engine cannot both be empty.`；中国区 Provider 默认必须显式传 `search_pro`。
- 独立 API 传 `search_recency_filter=oneMonth` 成功，因此公共 `time_range` 可以映射为 `oneDay`、`oneWeek`、`oneMonth`、`oneYear`。
- 独立 API 的返回数量不能完全当作本地上限：请求 `count=2` 加域名过滤实测返回 15 条，请求 `count=50` 实测返回 49 条。Provider 必须先把 `count` 限制在公共 `max_results` 范围，再对返回数组本地截断。
- 实测 71 字符搜索词仍返回 HTTP 200，说明当前服务没有按公开资料中的 70 字符限制拒绝该请求。Provider 不应自行截断用户查询；是否增加本地长度校验，留给实现时按公共参数契约决定。
- Chat 不显式传 `search_query` 也能返回回答和结构化搜索结果，但正式 Provider 应显式把公共 `query` 传入 `web_search.search_query`，避免搜索词由模型自行改写而导致行为不可控。
- Chat 使用 `search_result=true`、`require_search=true`、`search_engine=search_pro`、`count` 和 `result_sequence=after` 的完整请求成功；`require_search=false` 也能成功，但不能作为“必须联网”的实现默认值。

### 10.3 已确认的两个 Provider 实现契约

以下设计已于 2026-09-03 与用户确认，正式开发不再以本文之外的默认行为为准。

#### 共同约束

- Provider 名称固定为 `zhipu_web_search` 和 `zhipu_chat_search`。
- 第一版只支持中国区默认端点 `https://open.bigmodel.cn`，不支持 Z.AI 海外端点。
- 两个 Provider 使用独立凭据环境变量：`ZHIPU_WEB_SEARCH_API_KEY`、`ZHIPU_CHAT_SEARCH_API_KEY`。当前同一枚普通 Key 可以同时填入两者，但代码不设置 `ZHIPU_API_KEY` 通用回退，也不读取 Coding Plan 的 Key。
- 只接受现有公共参数 `query`、`max_results`、`time_range`；不把 `search_engine`、域名过滤、搜索提示词、结果顺序等上游细节暴露为公共参数。
- `max_results` 在 1–20 范围内映射为上游 `count`，并且解析后再次本地截断、按 URL 去重；不能假设上游严格遵守 `count`。
- `time_range` 映射为智谱原生值：`d → oneDay`、`w → oneWeek`、`m → oneMonth`、`y → oneYear`；未设置时省略该字段。
- 两个 Provider 第一版只实现非流式、单次请求；不在 Provider 内自动重试，不在 API 和 Chat 之间隐式 fallback。
- 所有 HTTP 错误、JSON 错误、超时和网络错误都必须脱敏，不回显响应体、异常文本或凭据。

#### `zhipu_web_search`

- API Key：`ZHIPU_WEB_SEARCH_API_KEY`。
- Base URL：`AGENT_WEB_SEARCH_ZHIPU_WEB_SEARCH_BASE_URL`，默认 `https://open.bigmodel.cn`；Provider 自己拼接 `/api/paas/v4/web_search`。
- 请求固定发送 `search_engine=search_pro` 和 `search_intent=false`；`count` 使用公共 `max_results`，`content_size` 固定为 `medium`。
- `search_query` 使用公共 `query` 原值；`search_recency_filter` 按共同约束映射。第一版不发送 `request_id`、`user_id`、`search_domain_filter`。
- 成功响应只解析顶层 `search_result[]`，映射 `title`、`link`、`content`、`publish_date` 到公共 `SearchResult`；缺少有效 URL 的项目丢弃，结果按 URL 去重并本地限量。
- `ProviderResponse.answer` 保持为空，`searched` 在收到合法搜索响应后为 `true`。

#### `zhipu_chat_search`

- API Key：`ZHIPU_CHAT_SEARCH_API_KEY`。
- Base URL：`AGENT_WEB_SEARCH_ZHIPU_CHAT_BASE_URL`，默认 `https://open.bigmodel.cn`；Provider 自己拼接 `/api/paas/v4/chat/completions`。
- 模型环境变量：`AGENT_WEB_SEARCH_ZHIPU_CHAT_MODELS`；默认模型固定为 `glm-5.3-flash`，支持逗号/换行分隔的多个模型，并复用现有模型池轮转。
- 每次请求都强制联网：`enable=true`、`search_engine=search_pro`、`search_result=true`、`require_search=true`、`result_sequence=after`；`search_query` 使用公共 `query` 原值，`count` 和 `search_recency_filter`按共同约束映射，`content_size=medium`。
- `messages` 使用一个 user 消息；消息内容复用项目现有 `search_prompt(query, time_range, max_results)`，搜索工具的 `search_query` 仍使用未改写的原始公共 query。这样既保证模型输出可读答案，又避免模型自行改写检索词。
- `answer` 解析首个 `choices` 元素的 `message.content`；`results` 只解析顶层 `web_search[]`，不从回答正文里的 URL 或 `ref_1` 字符串猜结果。回答非空但 `results` 为空是合法成功形态。
- `searched` 只在响应提供了可验证的顶层 `web_search` 数组时置为 `true`；不能仅凭 HTTP 200 或回答非空宣称搜索已执行。
- 响应中的 `model` 仅记录到 `ProviderResponse.model`，不用于替换模型池选择。

#### 必须覆盖的测试边界

- 两个 Provider 缺少各自 Key 时返回脱敏配置错误；一个 Provider 的 Key 不得被另一个 Provider 自动使用。
- 独立 API 请求必须断言 `search_engine=search_pro`、`search_intent=false`、count/recency 映射和本地截断；应覆盖上游返回多于 count 的情况。
- Chat 请求必须断言精确模型、`web_search` 嵌套对象、`enable/search_result/require_search/result_sequence` 的 boolean/string 类型和公共参数映射。
- Chat 解析至少覆盖“answer + results”和“answer + 空 results”；不得把回答正文 URL转换为结果。
- 两个 Provider 均覆盖 HTTP 401、429、5xx、超时、无效 JSON、非对象 JSON，并确认错误中不含测试凭据或上游响应正文。
- 注册表、环境变量、默认端点、默认模型和完整 pytest/Ruff 检查必须纳入实现 Agent 的验收。



## 11. 最终判断

把三种能力做成三个 Provider 是合理的，而且比一个混合 Provider 更适合这个项目。真正应该共享的是项目内部的 `Provider` 接口和结果标准化层；真正不应该共享的是三种上游协议的请求和响应解析。

唯一需要控制的是 Provider 数量命名：名称应体现语义和协议，不要再往一个 Provider 里塞“自动选择 API/MCP/Chat”的隐式 fallback。这样每个 Provider 的能力、凭据、失败原因和测试边界都能单独说明，也符合当前项目“多个相互独立 Provider”的整体设计。[16]

## Sources

[3] https://docs.bigmodel.cn/cn/coding-plan/mcp/search-mcp-server — 智谱 联网搜索 MCP
[5] https://docs.bigmodel.cn/api-reference/%E5%B7%A5%E5%85%B7-api/%E7%BD%91%E7%BB%9C%E6%90%9C%E7%B4%A2 — 智谱 网络搜索 API
[9] https://docs.z.ai/devpack/mcp/search-mcp-server — Z.AI Web Search MCP
[10] https://docs.z.ai/api-reference/tools/web-search — Z.AI Web Search API
[11] https://docs.bigmodel.cn/cn/guide/tools/web-search
[12] https://docs.bigmodel.cn/api-reference/%E6%A8%A1%E5%9E%8B-api/%E5%AF%B9%E8%AF%9D%E8%A1%A5%E5%85%A8
[14] https://docs.z.ai/api-reference/llm/chat-completion
[15] https://pypi.org/project/zai-sdk
[16] https://modelcontextprotocol.io/specification/2025-06-18/server/tools
