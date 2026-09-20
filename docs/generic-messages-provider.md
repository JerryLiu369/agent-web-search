# Generic Anthropic Messages API Search Provider 设计与实现规范

> **规范版本**：v1.0  
> **制定日期**：2026-09-20  
> **所属仓库**：`JerryLiu369/agent-web-search`  
> **目标**：为 `agent-web-search` 引入通用的 Anthropic Messages 协议检索 Provider（`messages`），与现有的 `responses`（OpenAI 阵营）形成完整的“双协议”对称矩阵。

---

## 1. 背景与核心价值

当前项目中，`deepseek.py` 已经验证了 Anthropic Messages 协议 + 原生 Web Search 能够产生高质量模型 Grounding 结果。但其代码与 DeepSeek 的官方域名、Key 和默认模型高度绑定。

随着 Claude 官方及各大兼容网关陆续支持 `/v1/messages` 协议与服务器端搜索能力（如 `web_search_20250305`），我们需要一个**完全通用、厂商中立的 Generic Messages Provider**：
1. **协议泛化**：任何兼容 Anthropic `/v1/messages` 且支持服务端 Web Search 的端点（Anthropic 官方、第三方中转、自建网关等）均可即插即用；
2. **多模型轮询池**：支持配置模型列表（如 `claude-3-7-sonnet-20250219,claude-3-5-haiku-20241022`）及循环负载均衡；
3. **可定制工具类型与名称**：默认 `web_search_20250305`，亦可通过环境变量自定义覆盖；
4. **统一契约**：输出标准的 `ProviderResponse(provider="messages", answer=..., results=...)`，包含 `title`, `url`, `description`。

---

## 2. 详细设计规格

### 2.1 环境变量设计

遵循既有规范（前缀 `AGENT_WEB_SEARCH_MESSAGES_*`）：

| 环境变量 | 默认值 | 作用说明 |
| :--- | :--- | :--- |
| `AGENT_WEB_SEARCH_MESSAGES_API_KEY` | *(无，必须)* | 认证 Key，请求头写入 `x-api-key` |
| `AGENT_WEB_SEARCH_MESSAGES_BASE_URL` | `https://api.anthropic.com` | 上游基地址，支持自动规范化补齐 `/v1/messages` |
| `AGENT_WEB_SEARCH_MESSAGES_ENDPOINT` | *(可选)* | 完整端点覆盖（若提供则优先于 Base URL） |
| `AGENT_WEB_SEARCH_MESSAGES_MODELS` | `claude-3-7-sonnet-20250219,claude-3-5-haiku-20241022` | 模型轮询列表（逗号或换行分隔） |
| `AGENT_WEB_SEARCH_MESSAGES_TOOL_TYPE`| `web_search_20250305` | Anthropic 搜索工具类型 |
| `AGENT_WEB_SEARCH_MESSAGES_TOOL_NAME`| `web_search` | 工具名称标识 |
| `AGENT_WEB_SEARCH_MESSAGES_TIMEOUT`  | `60` | 请求超时上限（秒） |

---

### 2.2 Wire Protocol 请求构造

* **HTTP 方法**：`POST {base_url}/v1/messages`
* **HTTP Headers**：
  ```http
  Content-Type: application/json
  x-api-key: <API_KEY>
  anthropic-version: 2023-06-01
  ```
* **Payload 结构**：
  ```json
  {
    "model": "<SELECTED_MODEL>",
    "max_tokens": 4096,
    "messages": [
      {
        "role": "user",
        "content": "<SEARCH_PROMPT>"
      }
    ],
    "tools": [
      {
        "type": "<TOOL_TYPE>",
        "name": "<TOOL_NAME>",
        "max_uses": 5
      }
    ]
  }
  ```
  *(注：Prompt 构造复用 `search_prompt(request.query, time_range=request.time_range, max_results=request.max_results)`)*

---

### 2.3 响应解析与数据抽取

响应数据顶层为 JSON 对象，包含 `content` 数组：

1. **Answer 提取**：
   - 遍历 `content`，找到 `type == "text"` 的块；
   - 累加或取正文 `text`，作为最终的 `answer`；
   - 支持解析 text 块中的 `citations`（若存在）；
2. **搜索触发状态 (`searched`)**：
   - 当 `content` 中存在 `type in {"server_tool_use", "tool_use", "web_search_tool_result"}` 时，置 `searched = True`；
3. **检索结果列表 (`results`) 提取**：
   - 解析 `type == "web_search_tool_result"` 内部的子块，或直接出现在 `content` 中的 `type == "web_search_result"` 块；
   - 抽取字段：
     - `url`：必须字段，去重并过滤空值；
     - `title`：网页标题（若缺失，尝试通过 citation 回填或降级为域名）；
     - `description`：取 `description` 或 `snippet` 字段；
   - 结果列表截断至 `request.max_results`。

---

### 2.4 模块归属与注册

1. **新建模块**：`agent_web_search/providers/messages.py`
   - 定义 `MessagesProvider(Provider)` 类；
   - 实现 `name = "messages"`，静态方法 `parse`，以及 `search(request: SearchRequest)` 方法；
2. **Provider 注册**：
   - 在 `agent_web_search/providers/__init__.py` 中暴露 `MessagesProvider`；
   - 在 `agent_web_search/registry.py` 的 `PROVIDER_SPECS` 中注册：
     ```python
     "messages": ProviderSpec(
         MessagesProvider,
         "Generic Anthropic Messages API web search",
         "AGENT_WEB_SEARCH_MESSAGES_API_KEY",
     ),
     ```
3. **外围元数据与文档同步**：
   - `server.json`：声明 `AGENT_WEB_SEARCH_MESSAGES_API_KEY` 与 `AGENT_WEB_SEARCH_MESSAGES_BASE_URL`；
   - `.env.example`、`plugin.yaml`、双语 `README.md` 与 Skills 同步增加说明。

---

### 2.5 测试规范要求

新增单元测试文件 `tests/test_messages_provider.py`：
1. **Mock 成功用例**：
   - 包含标准 text 总结与多个 `web_search_tool_result` 结果；
   - 验证 `answer`、`results`（URL, Title, Description）、`searched` 状态解析完全正确；
2. **边缘场景用例**：
   - `content` 中包含思考块（`thinking`）或异常块，验证不崩溃；
   - 缺失 `title` 时的回填或降级；
   - 搜索未触发（纯文本回答）时的行为；
3. **错误处理用例**：
   - API Key 未设置时返回正确错误结构；
   - HTTP 401、429、500 时通过 `http_error` 映射；
   - 网络异常时通过 `exception_error` 映射；
4. **质量门禁**：
   - 运行 `pytest` 全仓测试必须 100% 通过（226+ 个单测全绿）；
   - 运行 `ruff check .` 和 `ruff format --check .` 必须零违规。
