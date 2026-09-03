# DeepSeek / Z.AI 搜索 Provider 实施计划

> 状态：仅规划，尚未实现。本文档只保留在开发分支 `feat/deepseek-zai-search-providers`；功能完成并准备合并 `main` 前删除，历史由 Git 保留。

## 1. 目标

分阶段增加三个公开 Provider，每次只实现、实测和验收一个：

1. `deepseek`：DeepSeek Responses API 原生 `web_search`。
2. `zai`：GLM Chat Completions 中注入 `web_search` 工具，由模型搜索并生成回答。
3. `zai_search`：智谱/Z.AI 结构化搜索，统一支持普通 Web Search API 和 Coding Plan Remote MCP。

搜索智能体（Search Agent）不在本轮范围内。

## 2. Provider 边界

| Provider | 类型 | 主要输出 | 上游形态 |
| --- | --- | --- | --- |
| `deepseek` | 模型原生搜索 | `answer` + 可提取的 URL 引用 | Responses API + `web_search` |
| `zai` | 模型原生搜索 | `answer` + 上游实际返回的来源 | Chat Completions + `tools.web_search` |
| `zai_search` | 结构化搜索 | `results` | Web Search REST API 或 `webSearchPrime` MCP |

不按中国/海外拆 Provider。地域由服务 URL 决定；普通 API 与 Coding Plan MCP 是 `zai_search` 的两种显式 transport，也不拆成 `zai_search_api` / `zai_plan`。

## 3. 统一响应契约

保持现有公共响应不变：

```json
{
  "query": "...",
  "providers": {
    "provider_name": {
      "answer": "可选；上游生成回答时才出现",
      "results": [
        {
          "title": "",
          "url": "",
          "description": "",
          "published_at": "可选",
          "author": "可选"
        }
      ]
    }
  }
}
```

约束：

- `results` 始终存在，可以为空。
- `answer`、`published_at`、`author` 没值时省略。
- 不把网站名称 `media` 冒充作者；没有可靠作者字段就不输出 `author`。
- 不伪造引用。模型只返回 `ref_1` 而没有 URL 映射时，保留 `answer`，允许 `results=[]`。
- Provider 凭据、模型名、transport 和执行元数据不进入公共响应。

## 4. 配置草案

全部保持环境变量配置，不增加 YAML/JSON 配置文件。

### 4.1 DeepSeek

```text
DEEPSEEK_API_KEY                         必填
AGENT_WEB_SEARCH_DEEPSEEK_BASE_URL       可选，默认官方 API
AGENT_WEB_SEARCH_DEEPSEEK_MODELS         可选，逗号/换行分隔
```

默认模型和默认 URL 必须在真实 API 冒烟后锁定，不能仅根据文档猜测。

### 4.2 Z.AI 模型原生搜索

```text
ZAI_API_KEY                              必填
AGENT_WEB_SEARCH_ZAI_BASE_URL            可选，中国/海外或兼容代理
AGENT_WEB_SEARCH_ZAI_MODELS              可选，逗号/换行分隔
```

`zai` 只表示模型原生 `web_search`，不承担普通搜索 API 或 MCP。

### 4.3 Z.AI 结构化搜索

```text
AGENT_WEB_SEARCH_ZAI_SEARCH_TRANSPORT    api | mcp，显式选择
AGENT_WEB_SEARCH_ZAI_SEARCH_URL          可选，中国/海外或兼容代理
ZAI_API_KEY                              api transport 使用
ZAI_PLAN_API_KEY                         mcp transport 使用
```

原则：

- 不根据 URL 路径自动猜 transport，自定义代理 URL 可能不含 `/mcp/`。
- 两种 Key 分开，避免普通平台 Key 与 Coding Plan Key 混用。
- 如果真实测试证明海外/国内凭据命名或鉴权不同，再调整变量；第一阶段不提前扩展别名。

候选官方 URL（实现前逐一验证）：

```text
中国普通 API: https://open.bigmodel.cn/api/paas/v4/web_search
中国 Plan MCP: https://open.bigmodel.cn/api/mcp/web_search_prime/mcp
海外普通 API: https://api.z.ai/api/paas/v4/web_search
海外 Plan MCP: https://api.z.ai/api/mcp/web_search_prime/mcp
```

## 5. 实施顺序

### 阶段 0：API 证据采集

每个 Provider 开始编码前，先用用户提供的对应 Key 做一个最小真实请求，并保存脱敏结论，不保存凭据。

每次必须确认：

- 实际 URL、鉴权 Header 和 Key 所属产品。
- 可用模型名或 MCP 工具名。
- 最小请求体及必填字段。
- 非流式、流式或 SSE/JSON 响应形态。
- 回答、引用、搜索结果及错误字段的真实位置。
- 空结果、无引用、401、额度不足、模型不支持搜索时的错误形态。
- `max_results`、`time_range` 能否上游映射；不能映射时仅做提示词约束或本地截断。

真实响应只以脱敏测试 fixture 或字段摘要进入仓库，禁止提交 API Key、Authorization Header、账户信息及完整敏感查询。

### 阶段 1：实现 `deepseek`

#### API 探测

验证 Responses API：

- `tools=[{"type":"web_search"}]` 是否可用。
- 是否需要强制 `tool_choice`。
- 实际可用模型及默认模型。
- `web_search_call`、回答文本和 `url_citation` 的真实结构。
- 搜索续写/多轮执行、超时和费用相关行为。

#### 代码

- 新增 `agent_web_search/providers/deepseek.py`。
- 复用现有 `search_prompt()`、模型池及标准库 HTTP 风格。
- 从模型消息提取 `answer`；从 URL citation 去重生成 `results`。
- 无 citation 时保留正常回答，不把它误判为请求失败。
- 注册 Provider，补 `.env.example`、中英文 README 和 Skill 文档。

#### 测试与验收

- 请求体、鉴权、模型轮询。
- 多消息块、无 annotation、重复 URL、空 URL、异常响应。
- 401/429/5xx、超时及错误信息脱敏。
- 真实 CLI 冒烟：响应中出现 `deepseek`，公共结构不变。

完成后独立提交，不顺带实现 `zai`。

### 阶段 2：实现 `zai`

#### API 探测

验证 Chat Completions 工具注入：

- `tools[].type="web_search"` 的完整有效请求。
- `enable`、`search_result`、`search_engine`、`count`、`content_size` 的真实类型，不照抄文档示例中的字符串写法。
- 哪些 GLM 模型支持该工具。
- `search_result=true` 后是否真实返回结构化来源，还是只在回答中出现 `ref_1`。
- 来源 URL、标题、发布时间的真实位置和引用关联方式。

#### 代码

- 新增 `agent_web_search/providers/zai.py`。
- 使用 GLM Chat Completions + 原生 `web_search`。
- `choices[0].message.content` 映射为 `answer`。
- 只把上游明确提供的 URL 来源映射为 `results`；无法解析的 `ref_N` 不伪造 URL。
- 尽力把 `max_results`、`time_range` 映射到工具参数，其余通过统一搜索提示词表达。

#### 测试与验收

- 只有回答、回答加来源、工具未执行、空 choices、多个 choices。
- 搜索参数类型和支持模型。
- 401/429/模型不支持工具/内容过滤等错误。
- 真实 CLI 冒烟允许合法的 `answer + results=[]`。

完成后独立提交，不顺带实现 `zai_search`。

### 阶段 3A：实现 `zai_search` 的 API transport

#### API 探测

验证 Web Search API：

- 中国和海外端点各自可用性及 Key 是否跨区可用。
- `search_query`、`search_engine`、`count`、`search_domain_filter`、`search_recency_filter`、`content_size`。
- `search_result[]` 的实际字段及字段可选性。
- `count` 的真实允许值与当前公共 `max_results=1..20` 的映射。
- d/w/m/y 到官方 recency 枚举的精确映射。

#### 代码

- 新增 `agent_web_search/providers/zai_search.py` 和共享结果解析器。
- 映射：`title → title`、`link/url → url`、`content/summary → description`、`publish_date → published_at`。
- `media`、`icon`、`refer` 保持内部或忽略，不扩展公共 Schema。
- 首次只启用 `transport=api`。

#### 测试与验收

- 完整结果、缺少可选字段、无 URL 行、重复 URL、空结果。
- 请求参数、时间范围、数量截断和错误处理。
- 中国/海外至少各完成一次真实冒烟；若用户暂时只有一侧凭据，另一侧明确保留为未验证状态，不能宣称已支持。

完成后独立提交。

### 阶段 3B：为 `zai_search` 增加 MCP transport

#### API 探测

使用真实 Coding Plan Key 完成：

1. `initialize`
2. `notifications/initialized`
3. `tools/list`
4. `tools/call`

确认：

- 实际工具名及 input schema。
- 是否要求/返回 `MCP-Session-Id`。
- JSON 与 `text/event-stream` 响应支持情况。
- 结构化内容在 `structuredContent`、`content[].text` 或其他位置。
- MCP 返回的搜索行是否与普通 API 完全一致，还是仅语义一致。

#### 代码

- 在 `zai_search` 内增加 provider-local MCP 客户端，不增加第二个公开 MCP Server。
- 复用阶段 3A 的结果解析器。
- 显式 `transport=mcp` 时才读取 `ZAI_PLAN_API_KEY`。
- 保留 `isError`、HTTP 错误和 JSON-RPC 错误的真实诊断，同时清除凭据。

#### 测试与验收

- 初始化、通知、`tools/list`、`tools/call` 的完整序列。
- JSON/SSE、结构化响应/JSON 文本回退、工具错误、畸形响应。
- 普通 API 和 MCP 对同一组规范化 fixture 产生一致的公共结果行。
- 中国/海外按实际可获得的 Plan 凭据分别标记“实测”或“仅文档支持”。

完成后独立提交。

### 阶段 4：整体集成与发布准备

- 三个 Provider 可分别启用和请求级缩小，默认 Provider 集合保持不变。
- 裸环境及污染环境测试均通过，未配置 Key 的新 Provider 不影响现有启动。
- 更新 `.env.example`、README、README.zh-CN、Skill 和 `ARCHITECTURE.md`。
- 核对响应示例只把 `published_at`、`author` 标为可选。
- 做 CLI、stdio MCP、HTTP MCP 三条真实冒烟，确认共享 Schema 和错误语义一致。
- 每个新 Provider 的错误不得导致其他 Provider 被剔除。
- 最后确定版本号和发布说明；未完成全部真实 API 验证前不发布。

## 6. 每阶段固定质量门

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

同时执行：

- `git diff --check`
- 对应 Provider 的真实 CLI 冒烟
- stdio MCP `tools/list` + `tools/call`
- HTTP MCP 的同一工具调用（不改变公开 Schema）
- 检查日志、异常和测试 fixture 中没有 Key

只有“真实请求成功 + 解析结果符合统一契约 + 全量测试通过”才算该阶段完成。

## 7. 提交与分支纪律

本轮只在：

```text
feat/deepseek-zai-search-providers
```

开发，不直接修改或推送 `main`。

建议提交顺序：

```text
docs: plan DeepSeek and Z.AI search providers
feat: add DeepSeek native web search provider
feat: add Z.AI model-native web search provider
feat: add Z.AI structured Search API provider
feat: add Coding Plan MCP transport to Z.AI search
release: prepare <version>
```

每个实现提交必须独立可测、可回滚；不能在一个提交里同时落三个 Provider。准备合并前删除本计划文档，避免已完成的工作计划长期留在 `main`，完整过程由分支和 Git 历史保留。
