# Generic Responses API Search Provider 设计与实现规范

> **规范版本**：v1.0  
> **制定日期**：2026-09-20  
> **所属仓库**：`JerryLiu369/agent-web-search`  
> **目标**：为 `agent-web-search` 引入通用的 OpenAI Responses 协议检索 Provider（注册名：`responses`），实现对支持内置 Web Search 工具的下一代大模型与网关（如 OpenAI 官方 Responses API、CPA/Antigravity 路由的 Google Search Grounding、以及各类兼容网关）的通用标准化对接。

---

## 1. 架构背景与设计理念

### 1.1 为什么需要 Generic Responses Provider？
目前 `agent-web-search` 已经支持两类 Provider：
1. **纯搜索引擎 API**（如 Tavily、Exa、Brave、DuckDuckGo）：仅返回原始 URL 和文本切片，需上层调用者另行总结。
2. **特定厂商对话检索 API**（如 `zhipu_chat_search`、`gemini` Interactions）：强绑定了特定云厂商的专有私有格式。

随着 OpenAI Responses API（`/v1/responses`）正在成为大模型交互的事实标准，越来越多的新一代模型与网关开始原生支持服务端搜索工具：
* **OpenAI 官方**：`/v1/responses` 端点内置 `tools: [{"type": "web_search"}]`；
* **CLIProxyAPI (CPA)**：在 `/v1/responses` 下为 Google Antigravity / Gemini 实现了将 `web_search` 转换为原生 Google Search Grounding，并自动清洗 Vertex 重定向链接；
* **本地与开源网关**（如 AxonHub 等）：全面向 Responses API 协议收敛。

### 1.2 核心价值：一鱼两吃（Dual-Output Grounding）
Responses 协议调用在单次 HTTP 请求中自闭环完成“联网搜索 ➔ 深度阅读 ➔ 提取引用 ➔ 综合回答”，其返回的响应体天然包含两个维度的产物：
1. **结构化原始来源（Raw Sources）**：从 `web_search_call` 中提取搜索引擎真实命中的 URL 与 Title 列表；
2. **高置信度回答（Grounded Answer）**：从 `message` 中提取模型结合搜索结果生成的最终文本，并附带精确的 `url_citation` 行内引用。

通过通用 Responses Provider，`agent-web-search` 可以以极简的代码（~100 行），通吃所有支持该协议的网关与模型。

---

## 2. 接口契约与数据流

### 2.1 请求契约
* **请求端点**：`POST {base_url}/responses`
* **请求头**：
  ```http
  Authorization: Bearer <API_KEY>
  Content-Type: application/json
  User-Agent: agent-web-search/<version>
  ```
* **请求体 Schema**：
  ```json
  {
    "model": "<model_name>",
    "input": "<natural_language_search_prompt>",
    "tools": [
      {
        "type": "<tool_type>"
      }
    ]
  }
  ```
  * `model`：由模型池（Model Pool）按轮询分发，支持配置默认模型；
  * `input`：使用 `prompting.search_prompt(request.query, request.time_range)` 生成带时效约束的完整搜索 Prompt；
  * `tools`：包含一个指定类型的搜索工具，默认 `"web_search"`。

### 2.2 响应契约（OpenAI Responses Wire Format）
上游 Responses API 成功时返回 HTTP 200，其核心载荷位于顶层的 `output` 数组中：
```json
{
  "id": "resp_xxxxxxxx",
  "object": "response",
  "status": "completed",
  "model": "gemini-3.8-flash",
  "output": [
    {
      "id": "rs_reasoning_01",
      "type": "reasoning",
      "summary": "..."
    },
    {
      "id": "ws_call_01",
      "type": "web_search_call",
      "status": "completed",
      "action": {
        "type": "search",
        "query": "2026 US Open winner",
        "sources": [
          {
            "type": "url",
            "url": "https://www.usopen.org/news/...",
            "title": "US Open Official"
          }
        ]
      }
    },
    {
      "id": "msg_01",
      "type": "message",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "Alexander Zverev won the 2026 US Open men's singles...",
          "annotations": [
            {
              "type": "url_citation",
              "url": "https://www.usopen.org/news/...",
              "title": "usopen.org",
              "start_index": 0,
              "end_index": 53
            }
          ]
        }
      ]
    }
  ]
}
```

---

## 3. Provider 配置与环境变量规范

遵循 `agent-web-search` 的 Provider 显式启用与配置惯例：

| 环境变量 | 说明 | 默认值 |
| :--- | :--- | :--- |
| `AGENT_WEB_SEARCH_RESPONSES_ENDPOINT` | 基础 URL（Base URL） | 必须显式配置，如 `http://127.0.0.1:52718/v1` |
| `AGENT_WEB_SEARCH_RESPONSES_API_KEY` | 访问密钥（可从现有 `OPENAI_API_KEY` 或 `CPA_API_KEY` 回退） | 无 |
| `AGENT_WEB_SEARCH_RESPONSES_MODELS` | 模型池列表（逗号分隔） | `gemini-3.8-flash,gpt-4o` |
| `AGENT_WEB_SEARCH_RESPONSES_TOOL_TYPE`| 工具类型名称（兼容部分非标端点） | `web_search` |
| `AGENT_WEB_SEARCH_RESPONSES_TIMEOUT`  | 请求超时时间（秒） | `60` |

### 3.1 配置文件（`config.yaml`）支持
```yaml
providers:
  responses:
    endpoint: "http://127.0.0.1:52718/v1"
    api_key: "${CPA_API_KEY}"
    models:
      - "gemini-3.8-flash"
    tool_type: "web_search"
    timeout: 60
```

---

## 4. 核心解析与健壮性规范（Implementation Rules）

在 `agent_web_search/providers/responses.py` 中实现解析逻辑时，必须严格遵守以下规则：

### 4.1 遍历 `output` 数组，切忌硬编码下标
由于模型思考（CoT）的存在，`output` 数组的前置元素可能是 `type: "reasoning"`，因此**严禁假设 `output[0]` 即为搜索结果**：
1. **提取原始来源（Sources）**：
   - 查找 `type` 包含 `"web_search_call"` 或与配置的 `tool_type` 匹配的元素；
   - 从 `item.get("action", {}).get("sources", [])` 中遍历提取 `url` 与 `title`；
   - 过滤空 URL、规范化并做内存 Set 去重。
2. **提取模型回答（Answer & Citations）**：
   - 查找 `type == "message"` 的元素；
   - 遍历 `content` 数组，合并 `output_text` 或 `text` 字段作为最终的 `answer`；
   - 检查 `content.annotations`，若存在 `type == "url_citation"` 且具有有效 URL，将其同样视作搜索来源（补充可能未在 `sources` 数组中列出的引用网页）。
3. **标记有效检索（`searched` 状态）**：
   - 当检测到 `web_search_call` 完成，或成功提取到非空 `sources` / `url_citation` 时，标记 `searched = True`。

### 4.2 异常与错误处理
* **标准 HTTP 错误映射**：
  使用现有的 `http_error(e, "responses")` 捕获 `urllib.error.HTTPError`：
  - 401 ➔ 明确提示 API Key 无效或未提供；
  - 429 ➔ 标记限频，供调度引擎触发轮换/降级；
  - 5xx ➔ 捕获上游网关故障，记入 `failed_provider_errors`。
* **退化降级处理**：
  若模型上游未触发搜索（如知识库直接回答，`output` 中仅有 `message` 且无任何 URL），返回空 `results` 列表，保留 `answer`，并将 `searched` 置为 `False`。

---

## 5. 实现清单（Checklist）

执行模型或 Agent 实施时，应按以下顺序进行分支开发与测试：

- [ ] **1. 新建实现分支**：从最新 `main` 切出独立分支 `feat/provider-generic-responses`（不与其他未合并分支交叉污染）。
- [ ] **2. 实现核心逻辑**：
  - 新增 `agent_web_search/providers/responses.py`：实现 `ResponsesProvider(Provider)` 类，包含 `search` 与 `parse` 方法；
  - 在 `agent_web_search/providers/__init__.py` 中导出 `ResponsesProvider`；
  - 在 `agent_web_search/registry.py` 中注册 `"responses"`，并支持按环境变量与配置动态实例化。
- [ ] **3. 补齐单元测试**：
  - 新增 `tests/test_responses_provider.py`，使用 Mock 验证：
    - 包含 `reasoning` + `web_search_call` + `message` 的标准成功响应解析；
    - 仅有 `annotations` 无 `sources` 时的兼容解析；
    - 触发 401 / 429 / 500 时通过 `http_error` 正确抛出结构化异常；
    - 模型池轮询与环境变量读取逻辑。
- [ ] **4. CI 与代码规范校验**：
  - 运行 `ruff check .` 与 `ruff format --check .` 确保无代码风格违规；
  - 运行 `pytest tests/` 确保全量单测 PASS（无回归）。
- [ ] **5. 文档与类型更新**：
  - 在 `README.md` 与 `README.zh-CN.md` 的 Provider 支持表格中新增 `responses` 说明。
