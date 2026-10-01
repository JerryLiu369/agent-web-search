window.__ModuleLoader__.load({
	id: "dsh-agent-web-search",
	factory: (require) => {
		var module = { exports: {} };
		var exports = module.exports;
		Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
		const React = require("react");
		const h = React.createElement;

		//#region constants (mirrored from lib/defaults.js — a client bundle must not
		// value-import @deepseek-ai/* packages, and cannot reach the Host modules) */
		const NS = "agent-web-search";
		const PROVIDER_KINDS = ["exa", "parallel", "ddgs", "brave", "tavily", "perplexity", "you", "gemini", "grok", "ark", "zhipu_web_search", "zhipu_chat_search", "deepseek", "messages", "responses", "codex_alpha"];
		const KIND_LABEL = { exa: "Exa", parallel: "Parallel", ddgs: "DuckDuckGo", brave: "Brave Search", tavily: "Tavily", perplexity: "Perplexity", you: "You.com", gemini: "Gemini (Google Search grounding)", grok: "Grok", ark: "Volcengine ARK", zhipu_web_search: "Zhipu Web Search", zhipu_chat_search: "Zhipu Chat Search", deepseek: "DeepSeek", messages: "Anthropic Messages (generic)", responses: "OpenAI Responses (generic)", codex_alpha: "Codex Alpha (experimental)" };
		const KIND_CREDENTIAL_REF = { exa: "EXA_API_KEY", parallel: "PARALLEL_API_KEY", ddgs: null, brave: "BRAVE_SEARCH_API_KEY", tavily: "TAVILY_API_KEY", perplexity: "PERPLEXITY_API_KEY", you: "YDC_API_KEY", gemini: "GEMINI_API_KEY", grok: "XAI_API_KEY", ark: "ARK_API_KEY", zhipu_web_search: "ZHIPU_WEB_SEARCH_API_KEY", zhipu_chat_search: "ZHIPU_CHAT_SEARCH_API_KEY", deepseek: "DEEPSEEK_API_KEY", messages: "AGENT_WEB_SEARCH_MESSAGES_API_KEY", responses: "AGENT_WEB_SEARCH_RESPONSES_API_KEY", codex_alpha: "AGENT_WEB_SEARCH_CODEX_ALPHA_API_KEY" };
		const KIND_DEFAULT_BASE_URL = { exa: "https://mcp.exa.ai/mcp", parallel: "https://search.parallel.ai/mcp", brave: "https://api.search.brave.com/res/v1/web/search", tavily: "https://api.tavily.com/search", perplexity: "https://api.perplexity.ai/search", you: "https://ydc-index.io/v1/search", gemini: "https://generativelanguage.googleapis.com/v1beta/interactions", grok: "https://api.x.ai/v1/responses", ark: "https://ark.cn-beijing.volces.com/api/v3/responses", zhipu_web_search: "https://open.bigmodel.cn", zhipu_chat_search: "https://open.bigmodel.cn", deepseek: "https://api.deepseek.com", messages: "https://api.anthropic.com", responses: "https://api.openai.com/v1", codex_alpha: "https://gateway.example/v1/alpha/search" };
		// Mirrors ENDPOINT_OVERRIDE_KINDS: `ddgs` drives the `ddgs` library and reads
		// no endpoint variable, so the card must not offer it an endpoint field.
		const ENDPOINT_OVERRIDE_KINDS = PROVIDER_KINDS.filter(kind => kind !== "ddgs");
		const MODEL_ENV = { deepseek: "AGENT_WEB_SEARCH_DEEPSEEK_MODELS", gemini: "AGENT_WEB_SEARCH_GEMINI_MODELS", grok: "AGENT_WEB_SEARCH_GROK_MODELS", ark: "AGENT_WEB_SEARCH_ARK_MODELS", zhipu_chat_search: "AGENT_WEB_SEARCH_ZHIPU_CHAT_MODELS", messages: "AGENT_WEB_SEARCH_MESSAGES_MODELS", responses: "AGENT_WEB_SEARCH_RESPONSES_MODELS", codex_alpha: "AGENT_WEB_SEARCH_CODEX_ALPHA_MODEL" };
		const TOOL_TYPE_KINDS = ["messages", "responses"];
		const TOOL_NAME_KINDS = ["messages"];
		const KIND_DEFAULT_TOOL_TYPE = { messages: "web_search_20250305", responses: "web_search" };
		const KIND_DEFAULT_MODELS = { deepseek: "deepseek-v4-flash", gemini: "gemini-3.7-flash", grok: "grok-4.6", ark: "glm-5-2-260617, doubao-seed-2-1-turbo-260628, deepseek-v4-flash-ga-260731", zhipu_chat_search: "glm-5.3-flash", messages: "claude-3-7-sonnet-20250219, claude-3-5-haiku-20241022", responses: "gpt-5-mini", codex_alpha: "gpt-5.6-luna" };
		const ANONYMOUS_KINDS = ["exa", "parallel", "ddgs"];
		const MODES = ["fanout", "fallback"];
		const NUMERIC_FIELDS = ["attemptTimeoutMs", "totalTimeoutMs"];
		const BOOLEAN_FIELDS = ["dedupeByUrl", "includeAnswer"];
		const entryKey = (entry) => entry.kind;
		//#endregion

		//#region locales
		const en = {
			title: "Web search agents",
			description: "Aggregated multi-upstream search: query several providers at once and merge the answers.",
			loading: "Reading this plugin's settings…",
			unavailable: "This plugin is not loaded, so it cannot be configured right now.",
			readOnly: "This deployment stores settings read-only.",
			save: "Save",
			saving: "Saving…",
			discard: "Discard",
			saveFailed: "The deployment did not accept these values; they were left for you to correct.",
			invalidNumber: "Enter a whole number, or leave blank to use the default.",
			mode: "Search mode",
			modeFanout: "Fan out (all upstreams, merged)",
			modeFallback: "Fallback (first success wins)",
			modeHint: "Fanout queries every enabled upstream concurrently and merges the results. Fallback walks them in order and stops at the first success.",
			attemptTimeout: "Per-upstream timeout (ms)",
			totalTimeout: "Whole-search budget (ms)",
			dedupeByUrl: "De-duplicate by URL",
			includeAnswer: "Carry upstream prose answers",
			upstreams: "Upstreams",
			upstreamsHint: "Exa, Parallel and DuckDuckGo need no key at all. Every other row stays dormant until its credential is set.",
			history: "Recent search calls",
			selectedRoute: "Currently selected search route",
			notSelected: "This plugin is not the selected route; its call log will stay unchanged.",
			unknownRoute: "Unavailable",
			resultUnit: "results",
			cardTitle: "Web search",
			cardRunning: "Searching…",
			cardFailed: "Search failed",
			cardEmpty: "No results",
			cardTruncated: "The source list was cut.",
			historyHint: "Last 50 calls in this desktop process, one call per row. Scroll the log horizontally for all upstreams. Queries, keys and response bodies are never retained. Refreshes every 5 seconds.",
			historyEmpty: "No calls recorded yet.",
			historyError: "Could not read the authenticated call log.",
			historySuccess: "Returned",
			historyFailed: "Failed",
			historyAborted: "Cancelled",
			historyStatus_success: "success",
			historyStatus_empty: "empty (0 results)",
			historyStatus_failed: "failed",
			historyStatus_timeout: "timed out",
			historyStatus_cancelled: "cancelled",
			enabled: "On",
			endpoint: "Endpoint",
			key: "API key",
			keyConfigured: "Key configured",
			keyUnset: "No key configured",
			keyAnonymous: "No key needed",
			keyPlaceholder: "Paste a key",
			keyPlaceholderConfigured: "Saved (paste new key to replace)",
			keySaveHint: "The key is stored outside the settings file and never echoed back.",
			overridden: "Overridden",
			reset: "Reset",
			dirty: "Unsaved changes",
			pageIntro: "Choose search sources and inspect actual routes from one place.",
			tabSources: "Sources",
			tabPolicy: "Search policy",
			tabActivity: "Activity",
			sourceCount: "sources enabled",
			configure: "Configure",
			collapse: "Collapse",
			endpointHint: "Leave blank for the provider's default endpoint.",
			model: "Model",
			modelHint: "Comma-separated model names for this upstream; blank uses the backend default.",
			toolType: "Tool type",
			toolTypeHint: "Native tool type for this backend; blank uses the backend default.",
			toolName: "Tool name",
			toolNameHint: "Native tool name for the Messages backend; blank uses the backend default.",
			historyTime: "Time",
			historyState: "Status",
			historyMode: "Mode",
			historyTotal: "Results · duration",
			historyAttempts: "Upstream attempts",
			fanoutShort: "Fanout",
			fallbackShort: "Fallback",
			policyIntro: "Adjust how enabled sources run and how their answers are merged.",
			policyModeTitle: "Dispatch mode",
			policyModeDesc: "Whether to query all upstreams concurrently or fall back in sequence.",
			attemptTimeoutDesc: "Timeout limit for each individual upstream attempt.",
			totalTimeoutDesc: "Overall time budget across all upstreams before stopping.",
			dedupeByUrlDesc: "Automatically combine results that point to the exact same web URL.",
			includeAnswerDesc: "Include synthesized text summaries from upstreams that generate answers.",
			limitsGroup: "Timeout Budget",
			filterGroup: "Result Processing & Content",
			notSaved: "Changes take effect after saving.",
		};
		const zh = {
			title: "聚合搜索",
			description: "多上游聚合搜索：一次并发查询多个搜索引擎，合并去重后返回。",
			loading: "正在读取该插件的设置…",
			unavailable: "该插件当前未加载，暂时无法配置。",
			readOnly: "本部署的设置为只读。",
			save: "保存",
			saving: "保存中…",
			discard: "放弃修改",
			saveFailed: "本部署没有接受这些值，已保留供你修改。",
			invalidNumber: "请填整数；留空表示使用默认值。",
			mode: "搜索模式",
			modeFanout: "并发扇出（全部上游，合并结果）",
			modeFallback: "顺序回退（第一个成功即止）",
			modeHint: "扇出模式会并发查询所有启用的上游并合并结果；回退模式按顺序逐个尝试，第一个成功就停止。",
			attemptTimeout: "单上游超时（毫秒）",
			totalTimeout: "整体预算（毫秒）",
			dedupeByUrl: "按 URL 去重",
			includeAnswer: "携带上游的成文答案",
			upstreams: "上游列表",
			upstreamsHint: "Exa、Parallel、DuckDuckGo 完全不需要密钥；其余上游在配置凭据之前保持休眠。",
			history: "近期搜索调用",
			selectedRoute: "当前选中的搜索路由",
			notSelected: "当前未选中本插件；本插件的调用日志不会增加。",
			unknownRoute: "不可用",
			resultUnit: "条结果",
			cardTitle: "网页搜索",
			cardRunning: "搜索中…",
			cardFailed: "搜索失败",
			cardEmpty: "无结果",
			cardTruncated: "来源列表已被截断。",
			historyHint: "本次桌面进程最近 50 次调用，每次一行；横向滚动可查看全部上游。不会保存查询词、密钥或响应正文，每 5 秒刷新。",
			historyEmpty: "尚无搜索调用记录。",
			historyError: "无法读取经认证的调用日志。",
			historySuccess: "返回",
			historyFailed: "失败",
			historyAborted: "已取消",
			historyStatus_success: "成功",
			historyStatus_empty: "成功但无结果",
			historyStatus_failed: "失败",
			historyStatus_timeout: "超时",
			historyStatus_cancelled: "已取消",
			enabled: "启用",
			endpoint: "接口地址",
			key: "API Key",
			keyConfigured: "已配置密钥",
			keyUnset: "未配置密钥",
			keyAnonymous: "无需密钥",
			keyPlaceholder: "粘贴密钥",
			keyPlaceholderConfigured: "已保存（粘贴新密钥以替换）",
			keySaveHint: "密钥存放在设置文件之外，且从不回显。",
			overridden: "已覆盖",
			reset: "恢复默认",
			dirty: "有未保存的修改",
			pageIntro: "在这里选择搜索来源，并查看实际调用的路由。",
			tabSources: "搜索来源",
			tabPolicy: "搜索策略",
			tabActivity: "调用记录",
			sourceCount: "个来源已启用",
			configure: "配置",
			collapse: "收起",
			endpointHint: "留空则使用该来源的默认接口地址。",
			model: "模型",
			modelHint: "该上游的模型名，多个用逗号分隔；留空使用后端默认模型。",
			toolType: "工具类型",
			toolTypeHint: "该后端的原生工具类型；留空使用后端默认。",
			toolName: "工具名称",
			toolNameHint: "Messages 后端的原生工具名；留空使用后端默认。",
			historyTime: "时间",
			historyState: "状态",
			historyMode: "模式",
			historyTotal: "结果 · 耗时",
			historyAttempts: "上游尝试",
			fanoutShort: "并发",
			fallbackShort: "回退",
			policyIntro: "调整已启用来源的调用方式及答案合并方式。",
			policyModeTitle: "多上游调度模式",
			policyModeDesc: "选择并发查询全部上游以获取丰富结果，或顺序容灾以节省额度。",
			attemptTimeoutDesc: "单个搜索服务单次调用的最长等待时间（毫秒）。",
			totalTimeoutDesc: "聚合搜索全链路的最长预算耗时，超时将自动收敛（毫秒）。",
			dedupeByUrlDesc: "跨多个搜索来源发现相同网页 URL 时自动合并为一条引文。",
			includeAnswerDesc: "保留上游直接生成的智能成文总结（适用于 Perplexity、Exa 等）。",
			limitsGroup: "超时预算",
			filterGroup: "结果去重与内容偏好",
			notSaved: "修改保存后生效。",
		};
		//#endregion

		//#region store
		/**
		 * A minimal observable snapshot source (the shape `hooks` entries expose to
		 * a slot component). Deliberately tiny: the runtime contract is only
		 * `getSnapshot` + `subscribe`.
		 */
		function createStore(initial) {
			let value = initial;
			const listeners = new Set();
			return {
				getSnapshot: () => value,
				subscribe: (listener) => {
					listeners.add(listener);
					return () => {
						listeners.delete(listener);
					};
				},
				set: (next) => {
					value = next;
					for (const listener of [...listeners]) listener();
				},
			};
		}
		//#endregion

		//#region controller
		/**
		 * The staged form over the `agent-web-search` settings namespace.
		 *
		 * The queue is staged whole (one `providers` array write) while the scalar
		 * fields are staged per key, and credentials never enter the section at all:
		 * they are written through the credentials domain, addressed by the kind's
		 * fixed reference, and only their presence is read back.
		 */
		class CardController {
			constructor(scope, ctx) {
				this.scope = scope;
				this.ctx = ctx;
				this.shell = { available: false, writable: true, status: "loading", saving: false };
				/**
				 * Whether the last save was refused.
				 *
				 * Kept OUTSIDE `shell` on purpose: a refused write makes the Host
				 * reload the settings mirror, which lands right back here through the
				 * scope subscription. If this flag lived in `shell`, that reload would
				 * erase the very failure the user still has to read.
				 */
				this.failed = false;
				this.queue = [];
				this.queueDirty = false;
				this.edits = {};
				this.keyDrafts = {};
				this.credentials = {};
				this.store = createStore(this.projection());
				this.unsubscribe = scope.subscribe(() => {
					this.reseed();
				});
				this.reseed();
			}

			snapshot() {
				return this.scope.getSnapshot();
			}

			/**
			 * The mirror snapshot, narrowed to what the card reads.
			 *
			 * `writable` and `status` come from the same snapshot the values do — see
			 * `ConfigFormController` in `@deepseek-ai/dsh-client-ui-settings`, whose
			 * store starts at `status: 'loading'` for a Host-backed form and carries
			 * `writable: false` on a read-only deployment.
			 */
			layers() {
				const snapshot = this.snapshot();
				return {
					value: snapshot?.value ?? {},
					user: snapshot?.user ?? undefined,
					writable: snapshot?.writable !== false,
					status: typeof snapshot?.status === "string" ? snapshot.status : "loading",
				};
			}

			/** Re-read the scope, dropping staged drafts only when nothing is staged. */
			reseed() {
				const { value, writable, status } = this.layers();
				const available = typeof value === "object" && value !== null && Object.keys(value).length > 0;
				if (!available) {
					this.shell = { ...this.shell, available: false, writable, status };
					this.store.set(this.projection());
					return;
				}
				// A refused save reloads the mirror. The staged queue and drafts are
				// exactly what the user still has to correct, so that path must not
				// drop them; only the ordinary path (a change the card did not cause,
				// or an accepted save) re-seeds from the section.
				if (this.failed) {
					this.shell = { ...this.shell, available: true, writable, status };
					this.store.set(this.projection());
					return;
				}
				const seen = new Map();
				for (const entry of Array.isArray(value.providers) ? value.providers : []) {
					if (PROVIDER_KINDS.includes(entry?.kind) && !seen.has(entry.kind)) {
						seen.set(entry.kind, { kind: entry.kind, enabled: entry.enabled !== false, baseURL: typeof entry.baseURL === "string" ? entry.baseURL : "", models: typeof entry.models === "string" ? entry.models : "", toolType: typeof entry.toolType === "string" ? entry.toolType : "", toolName: typeof entry.toolName === "string" ? entry.toolName : "" });
					}
				}
				this.queue = PROVIDER_KINDS.map((kind) => seen.get(kind) ?? { kind, enabled: false, baseURL: "", models: "", toolType: "", toolName: "" });
				this.queueDirty = false;
				this.edits = {};
				this.keyDrafts = {};
				this.shell = { ...this.shell, available: true, writable, status };
				this.store.set(this.projection());
				this.readCredentials();
			}

			/** Ask the credentials domain which references currently hold a value. */
			async readCredentials() {
				const refs = this.queue.map((entry) => KIND_CREDENTIAL_REF[entry.kind]).filter((ref) => typeof ref === "string");
				try {
					const response = await this.ctx.remote.credentials.describe(refs);
					if (!response?.ok) return;
					this.credentials = response.value ?? {};
					this.store.set(this.projection());
				} catch {
					// A transport drop leaves the last known badges in place; the next
					// invalidation or reseed re-reads them.
				}
			}

			/** The value a control should render for one scalar field. */
			field(name) {
				if (Object.hasOwn(this.edits, name)) {
					const override = this.edits[name];
					const { value } = this.layers();
					return { text: override, overridden: value[name] !== undefined, explicit: true };
				}
				const { value, user } = this.layers();
				const current = value[name];
				return {
					text: current === undefined || current === null ? "" : String(current),
					overridden: user !== undefined && Object.hasOwn(user, name),
					explicit: false,
				};
			}

			projection() {
				const availability = {};
				for (const entry of this.queue) {
					const ref = KIND_CREDENTIAL_REF[entry.kind];
					if (ref === null) {
						availability[entryKey(entry)] = { state: "anonymous" };
						continue;
					}
					const view = this.credentials[ref];
					availability[entryKey(entry)] = {
						state: view?.configured === true ? "configured" : "unset",
						writable: view?.writable !== false,
					};
				}
				return {
					...this.shell,
					mode: this.field("mode"),
					attemptTimeoutMs: this.field("attemptTimeoutMs"),
					totalTimeoutMs: this.field("totalTimeoutMs"),
					dedupeByUrl: this.field("dedupeByUrl"),
					includeAnswer: this.field("includeAnswer"),
					queue: this.queue.map((entry) => ({
						...entry,
						draft: this.keyDrafts[entryKey(entry)] ?? "",
					})), 
					availability,
					dirty: this.isDirty(),
					invalid: this.validity(),
					// Deliberately after the spread: `shell` has no say over this flag.
					failed: this.failed,
				};
			}

			isDirty() {
				return this.queueDirty || Object.keys(this.edits).length > 0
					|| Object.values(this.keyDrafts).some((value) => value.trim().length > 0);
			}

			publish() {
				this.store.set(this.projection());
			}

			/**
			 * Stage a scalar edit. Every staging action clears the failure banner:
			 * the user is making a fresh attempt, so the previous refusal is stale.
			 */
			edit(name, text) {
				this.edits[name] = text;
				this.failed = false;
				this.publish();
			}

			resetField(name) {
				delete this.edits[name];
				this.failed = false;
				this.publish();
			}

			setEnabled(kind, enabled) {
				const entry = this.queue.find((row) => entryKey(row) === kind);
				if (entry === undefined) return;
				entry.enabled = enabled;
				this.queueDirty = true;
				this.failed = false;
				this.publish();
			}

			setBaseURL(kind, text) {
				const entry = this.queue.find((row) => entryKey(row) === kind);
				if (entry === undefined) return;
				entry.baseURL = text;
				this.queueDirty = true;
				this.failed = false;
				this.publish();
			}

			setModels(kind, text) {
				const entry = this.queue.find((row) => entryKey(row) === kind);
				if (entry === undefined) return;
				entry.models = text;
				this.queueDirty = true;
				this.failed = false;
				this.publish();
			}

			setToolType(kind, text) {
				const entry = this.queue.find((row) => entryKey(row) === kind);
				if (entry === undefined) return;
				entry.toolType = text;
				this.queueDirty = true;
				this.failed = false;
				this.publish();
			}

			setToolName(kind, text) {
				const entry = this.queue.find((row) => entryKey(row) === kind);
				if (entry === undefined) return;
				entry.toolName = text;
				this.queueDirty = true;
				this.failed = false;
				this.publish();
			}

			setKeyDraft(kind, text) {
				this.keyDrafts[kind] = text;
				this.failed = false;
				this.publish();
			}

			discard() {
				this.failed = false;
				this.reseed();
			}

			/** Coerce one staged scalar, or report it as invalid. */
			coerce(name) {
				const { text } = this.field(name);
				const trimmed = text.trim();
				if (trimmed.length === 0) return { ok: true, value: undefined };
				if (BOOLEAN_FIELDS.includes(name)) {
					if (trimmed === "true" || trimmed === "false") return { ok: true, value: trimmed === "true" };
					return { ok: false };
				}
				if (name === "mode") return MODES.includes(trimmed) ? { ok: true, value: trimmed } : { ok: false };
				const parsed = Number(trimmed);
				if (!Number.isInteger(parsed)) return { ok: false };
				return { ok: true, value: parsed };
			}

			validity() {
				for (const name of [...NUMERIC_FIELDS, ...BOOLEAN_FIELDS, "mode"]) {
					if (!Object.hasOwn(this.edits, name)) continue;
					if (!this.coerce(name).ok) return name;
				}
				return undefined;
			}

			/**
			 * Await one Host write and report whether it landed.
			 *
			 * The two seams this card writes through answer differently and both
			 * shapes have to be honoured:
			 *  - `configForms` scope writes (`set(field, value)` / `unset(field)`)
			 *    resolve to a bare boolean — `false` means the Host refused, after
			 *    having already reloaded the mirror. See `ConfigFormController.mutate`
			 *    in `@deepseek-ai/dsh-client-ui-settings`.
			 *  - the `remote.*` namespaces (`credentials.set/unset`) resolve to a
			 *    Remote envelope, `{ ok: true, value }` or `{ ok: false, error }`.
			 *    See `createModelsOperations` in `@deepseek-ai/dsh-client-ui-settings-models`.
			 *
			 * Anything thrown, or any other shape, counts as not landed: this card
			 * would rather say "the deployment did not accept these values" than
			 * claim a save that never happened.
			 * @param fn - the deferred write.
			 * @returns whether the Host accepted it.
			 */
			async writeSetting(fn) {
				try {
					const result = await fn();
					if (typeof result === "boolean") return result;
					return result?.ok === true;
				} catch {
					return false;
				}
			}

			async save() {
				if (this.shell.saving || !this.isDirty() || this.validity() !== undefined) return;
				this.shell = { ...this.shell, saving: true };
				this.failed = false;
				this.publish();
				let landed = true;

				// Credentials first: they live outside the section, and a refused write
				// should not leave the settings half-committed.
				for (const entry of this.queue) {
					const key = entryKey(entry);
					const draft = this.keyDrafts[key];
					if (typeof draft !== "string" || draft.trim().length === 0) continue;
					const ref = KIND_CREDENTIAL_REF[entry.kind];
					if (typeof ref !== "string") continue;
					const outcome = await this.writeSetting(() => this.ctx.remote.credentials.set(ref, draft.trim()));
					if (outcome) delete this.keyDrafts[key];
					else landed = false;
				}
				if (!landed) {
					// An old id must not reach a new URL when the replacement token failed.
					this.failed = true;
					this.shell = { ...this.shell, saving: false };
					this.publish();
					return;
				}

				if (this.queueDirty) {
					const payload = this.queue
						.filter((entry) => entry.enabled || entry.baseURL.trim().length > 0)
						.map((entry) => ({
							kind: entry.kind,
							enabled: entry.enabled,
							baseURL: entry.baseURL.trim(),
							...(typeof entry.models === "string" && entry.models.trim().length > 0 ? { models: entry.models.trim() } : {}),
							...(typeof entry.toolType === "string" && entry.toolType.trim().length > 0 ? { toolType: entry.toolType.trim() } : {}),
							...(typeof entry.toolName === "string" && entry.toolName.trim().length > 0 ? { toolName: entry.toolName.trim() } : {}),
						}));
					if (!await this.writeSetting(() => this.scope.set("providers", payload))) landed = false;
				}

				for (const [name] of Object.entries(this.edits)) {
					const coerced = this.coerce(name);
					if (!coerced.ok) {
						landed = false;
						continue;
					}
					const write = coerced.value === undefined
						? () => this.scope.unset(name)
						: () => this.scope.set(name, coerced.value);
					if (!await this.writeSetting(write)) landed = false;
				}

				// Order matters here, and getting it wrong silently swallowed the
				// failure: `reseed()` re-reads the mirror, and an ACCEPTED save should
				// re-seed the drafts from the new section. A refused one must not — the
				// staged values are exactly what the user has left to fix — so the flag
				// goes up first and `reseed()` keeps them while it is set.
				if (landed) {
					this.shell = { ...this.shell, saving: false };
					this.reseed();
				} else {
					this.failed = true;
					this.shell = { ...this.shell, saving: false };
					this.publish();
				}
				await this.readCredentials();
			}

			inject() {
				return {
					hooks: { agentWebSearch: this.store },
					// Every action returns its settlement, so a caller that wants to know
					// when a write finished can await it instead of polling the snapshot.
					save: () => this.save(),
					discard: () => this.discard(),
					edit: (name, text) => this.edit(name, text),
					resetField: (name) => this.resetField(name),
					setEnabled: (kind, enabled) => this.setEnabled(kind, enabled),
					setBaseURL: (kind, text) => this.setBaseURL(kind, text),
					setKeyDraft: (kind, text) => this.setKeyDraft(kind, text),
					setModels: (kind, text) => this.setModels(kind, text),
					setToolType: (kind, text) => this.setToolType(kind, text),
					setToolName: (kind, text) => this.setToolName(kind, text),
				};
			}

			dispose() {
				this.unsubscribe();
			}
		}
		//#endregion

		//#region presentation
		/**
		 * Refined desktop PC presentation with compact, modern controls and clean
		 * hover actions, strictly styled on the DSH alias palette (`--dsw-alias-*`).
		 */
		const CONTROL = {
			font: "inherit",
			fontSize: "13px",
			lineHeight: "20px",
			borderRadius: "6px",
			border: "1px solid var(--dsw-alias-border-l2)",
			background: "var(--dsw-alias-bg-layer-1)",
			color: "var(--dsw-alias-label-primary)",
			outlineColor: "var(--dsw-alias-brand-primary)",
			boxSizing: "border-box",
			transition: "border-color 0.15s ease, background-color 0.15s ease",
		};
		const DISABLED_TEXT = { color: "var(--dsw-alias-label-secondary)", cursor: "default", opacity: .55 };

		const INTERACTIVE_CSS = `
.aws-tab { cursor: pointer !important; transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1) !important; user-select: none !important; }
.aws-tab:hover { border-color: rgba(255, 255, 255, 0.32) !important; background-color: var(--dsw-alias-bg-layer-2) !important; color: var(--dsw-alias-label-primary) !important; transform: translateY(-1px); }
.aws-tab:active { transform: translateY(0); }

.aws-header-btn { cursor: pointer !important; transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1) !important; user-select: none !important; }
.aws-header-btn:hover:not(:disabled) { border-color: rgba(255, 255, 255, 0.35) !important; background-color: rgba(255, 255, 255, 0.1) !important; color: var(--dsw-alias-label-primary) !important; transform: translateY(-1px); }
.aws-header-btn:active:not(:disabled) { transform: translateY(0); }

.aws-interactive-row { cursor: pointer !important; transition: background-color 0.15s ease !important; }
.aws-interactive-row:hover { background-color: var(--dsw-alias-bg-layer-2) !important; }
.aws-interactive-row:hover .aws-row-title { color: var(--dsw-alias-label-primary) !important; }

.aws-icon-btn { cursor: pointer !important; transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1) !important; border-radius: 5px !important; }
.aws-icon-btn:hover:not(:disabled) { background-color: rgba(255, 255, 255, 0.14) !important; color: var(--dsw-alias-label-primary) !important; transform: scale(1.1); }
.aws-icon-btn:active:not(:disabled) { transform: scale(0.95); }

.aws-icon-btn-danger:hover:not(:disabled) { background-color: rgba(239, 68, 68, 0.16) !important; color: rgb(239, 68, 68) !important; transform: scale(1.1); }

.aws-switch { cursor: pointer !important; transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1) !important; }
.aws-switch:hover:not(:disabled) { border-color: var(--dsw-alias-brand-primary) !important; box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.08) !important; transform: scale(1.05); }
.aws-switch:active:not(:disabled) { transform: scale(0.97); }

.aws-checkbox { cursor: pointer !important; transition: transform 0.12s ease !important; }
.aws-checkbox:hover:not(:disabled) { transform: scale(1.18); }

.aws-btn { cursor: pointer !important; transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1) !important; }
.aws-btn:hover:not(:disabled) { border-color: rgba(255, 255, 255, 0.32) !important; background-color: var(--dsw-alias-bg-layer-2) !important; transform: translateY(-1px); }
.aws-btn:active:not(:disabled) { transform: translateY(0); }

.aws-btn-primary { cursor: pointer !important; transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1) !important; }
.aws-btn-primary:hover:not(:disabled) { filter: brightness(1.12) !important; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35) !important; transform: translateY(-1px); }
.aws-btn-primary:active:not(:disabled) { transform: translateY(0); }

.aws-input { transition: border-color 0.15s ease, background-color 0.15s ease, box-shadow 0.15s ease !important; }
.aws-input:hover:not(:disabled) { border-color: rgba(255, 255, 255, 0.28) !important; }
.aws-input:focus { border-color: var(--dsw-alias-brand-primary) !important; box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.1) !important; }

.aws-disclosure { cursor: pointer !important; transition: color 0.15s ease, background-color 0.15s ease !important; border-radius: 6px; }
.aws-disclosure:hover { color: var(--dsw-alias-brand-primary) !important; background-color: rgba(255, 255, 255, 0.04); }
`;

		function ensureInteractiveStyles() {
			if (typeof document !== "undefined" && !document.getElementById("aws-interactive-styles")) {
				const styleEl = document.createElement("style");
				styleEl.id = "aws-interactive-styles";
				styleEl.textContent = INTERACTIVE_CSS;
				document.head.appendChild(styleEl);
			}
		}

		// Lightweight vector icons for purely desktop experience
		function IconSettings({ size = 14, color = "currentColor", style = {} }) {
			return h("svg", {
				width: size, height: size, viewBox: "0 0 24 24", fill: "none",
				stroke: color, strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round",
				style: { display: "block", flexShrink: 0, ...style }
			},
				h("circle", { cx: "12", cy: "12", r: "3" }),
				h("path", { d: "M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" })
			);
		}

		function IconEye({ size = 14, color = "currentColor" }) {
			return h("svg", {
				width: size, height: size, viewBox: "0 0 24 24", fill: "none",
				stroke: color, strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round",
				style: { display: "block" }
			},
				h("path", { d: "M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" }),
				h("circle", { cx: "12", cy: "12", r: "3" })
			);
		}

		function IconEyeOff({ size = 14, color = "currentColor" }) {
			return h("svg", {
				width: size, height: size, viewBox: "0 0 24 24", fill: "none",
				stroke: color, strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round",
				style: { display: "block" }
			},
				h("path", { d: "M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" }),
				h("line", { x1: "1", y1: "1", x2: "23", y2: "23" })
			);
		}

		function IconAlert({ size = 14, color = "currentColor" }) {
			return h("svg", {
				width: size, height: size, viewBox: "0 0 24 24", fill: "none",
				stroke: color, strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round",
				style: { display: "block", flexShrink: 0 }
			},
				h("circle", { cx: "12", cy: "12", r: "10" }),
				h("line", { x1: "12", y1: "8", x2: "12", y2: "12" }),
				h("line", { x1: "12", y1: "16", x2: "12.01", y2: "16" })
			);
		}

		function IconReset({ size = 13, color = "currentColor", style = {} }) {
			return h("svg", {
				width: size, height: size, viewBox: "0 0 24 24", fill: "none",
				stroke: color, strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round",
				style: { display: "block", flexShrink: 0, ...style }
			},
				h("path", { d: "M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" }),
				h("path", { d: "M3 3v5h5" })
			);
		}

		function StatusDot({ color }) {
			return h("span", {
				style: {
					width: "6px",
					height: "6px",
					borderRadius: "50%",
					backgroundColor: color,
					display: "inline-block",
					flexShrink: 0,
				}
			});
		}

		const styles = {
			page: { maxWidth: "920px", margin: "0 auto", padding: "6px 4px 64px", color: "var(--dsw-alias-label-primary)", position: "relative", boxSizing: "border-box" },
			header: { marginBottom: "14px" },
			pageTitle: { fontSize: "18px", fontWeight: 600, letterSpacing: "-.01em", margin: "0 0 4px", color: "var(--dsw-alias-label-primary)" },
			hint: { fontSize: "12px", lineHeight: 1.5, color: "var(--dsw-alias-label-secondary)", margin: 0 },
			section: { padding: "10px 0 6px", marginBottom: "12px" },
			sectionHead: { fontSize: "14px", fontWeight: 600, lineHeight: 1.4, margin: "0 0 6px", color: "var(--dsw-alias-label-primary)" },
			row: { display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px", flexWrap: "wrap" },
			label: { fontSize: "13px", lineHeight: 1.4, color: "var(--dsw-alias-label-primary)" },
			badge: { display: "inline-flex", alignItems: "center", justifyContent: "center", gap: "5px", fontSize: "11px", lineHeight: "16px", width: "88px", height: "22px", borderRadius: "6px", border: "1px solid rgba(255, 255, 255, 0.14)", background: "rgba(255, 255, 255, 0.05)", color: "var(--dsw-alias-label-secondary)", userSelect: "none", boxSizing: "border-box", flexShrink: 0 },
			badgeOk: { display: "inline-flex", alignItems: "center", justifyContent: "center", gap: "5px", fontSize: "11px", lineHeight: "16px", width: "88px", height: "22px", borderRadius: "6px", border: "1px solid rgba(16, 185, 129, 0.38)", background: "rgba(16, 185, 129, 0.12)", color: "var(--dsw-alias-state-success-primary)", userSelect: "none", boxSizing: "border-box", flexShrink: 0 },
			badgeAnon: { display: "inline-flex", alignItems: "center", justifyContent: "center", gap: "5px", fontSize: "11px", lineHeight: "16px", width: "88px", height: "22px", borderRadius: "6px", border: "1px solid rgba(14, 165, 233, 0.38)", background: "rgba(14, 165, 233, 0.12)", color: "rgb(14, 165, 233)", userSelect: "none", boxSizing: "border-box", flexShrink: 0 },
			input: { ...CONTROL, height: "30px", minHeight: "30px", padding: "0 10px" },
			inputNum: { ...CONTROL, height: "30px", minHeight: "30px", padding: "0 8px", width: "90px" },
			select: { ...CONTROL, height: "30px", minHeight: "30px", padding: "0 8px", cursor: "pointer" },
			textarea: { ...CONTROL, padding: "8px 10px", width: "100%", minHeight: "80px", resize: "vertical", fontFamily: "ui-monospace, monospace", fontSize: "12px", lineHeight: 1.5 },
			entry: { borderBottom: "1px solid var(--dsw-alias-border-l1)", padding: "1px 0", marginBottom: "1px", minWidth: 0 },
			entryHead: { display: "flex", alignItems: "center", gap: "8px", minHeight: "34px", padding: "2px 6px", borderRadius: "6px", transition: "background-color 0.15s ease" },
			entryName: { fontSize: "13px", fontWeight: 500, lineHeight: 1.4, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "var(--dsw-alias-label-primary)" },
			spacer: { flex: 1, minWidth: 0 },
			tabs: { display: "flex", gap: "6px", margin: "12px 0 16px", padding: 0 },
			tab: { appearance: "none", border: "1px solid rgba(255, 255, 255, 0.12)", background: "var(--dsw-alias-bg-layer-1)", color: "var(--dsw-alias-label-secondary)", borderRadius: "6px", padding: "0 14px", height: "30px", minHeight: "30px", font: "inherit", fontSize: "13px", cursor: "pointer", transition: "all 0.15s ease", outlineColor: "var(--dsw-alias-brand-primary)", display: "inline-flex", alignItems: "center", boxSizing: "border-box" },
			tabActive: { border: "1px solid rgba(255, 255, 255, 0.28)", background: "var(--dsw-alias-bg-layer-2)", color: "var(--dsw-alias-label-primary)", fontWeight: 600 },
			button: { appearance: "none", font: "inherit", fontSize: "13px", padding: "0 12px", height: "30px", minHeight: "30px", borderRadius: "6px", border: "1px solid var(--dsw-alias-border-l2)", background: "var(--dsw-alias-bg-layer-1)", color: "var(--dsw-alias-label-primary)", cursor: "pointer", outlineColor: "var(--dsw-alias-brand-primary)", display: "inline-flex", alignItems: "center", justifyContent: "center", gap: "5px", transition: "background-color 0.15s ease, border-color 0.15s ease" },
			buttonPrimary: { appearance: "none", font: "inherit", fontSize: "13px", padding: "0 14px", height: "30px", minHeight: "30px", borderRadius: "6px", border: "1px solid var(--dsw-alias-brand-primary)", background: "var(--dsw-alias-brand-primary)", color: "var(--dsw-alias-bg-base)", fontWeight: 600, cursor: "pointer", outlineColor: "var(--dsw-alias-brand-primary)", display: "inline-flex", alignItems: "center", justifyContent: "center", gap: "5px", transition: "opacity 0.15s ease" },
			iconBtn: { appearance: "none", border: "none", background: "transparent", color: "var(--dsw-alias-label-secondary)", borderRadius: "5px", width: "26px", height: "26px", display: "inline-flex", alignItems: "center", justifyContent: "center", cursor: "pointer", padding: 0, transition: "background-color 0.15s ease, color 0.15s ease, opacity 0.15s ease", outlineColor: "var(--dsw-alias-brand-primary)", flexShrink: 0 },
			iconBtnActive: { background: "var(--dsw-alias-bg-layer-2)", color: "var(--dsw-alias-brand-primary)" },
			floatingBar: { position: "sticky", bottom: "16px", zIndex: 50, margin: "20px 0 0", padding: "8px 14px", borderRadius: "8px", background: "var(--dsw-alias-bg-layer-2)", border: "1px solid var(--dsw-alias-border-l2)", boxShadow: "0 8px 24px rgba(0, 0, 0, 0.35)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", backdropFilter: "blur(12px)" },
			panel: { background: "var(--dsw-alias-bg-layer-2)", border: "1px solid var(--dsw-alias-border-l1)", borderRadius: "8px", padding: "12px 14px", margin: "4px 0 8px", display: "grid", gap: "10px", minWidth: 0 },
			notice: { fontSize: "12px", lineHeight: 1.5, color: "var(--dsw-alias-label-secondary)", margin: "0 0 10px" },
			error: { flex: 1, minWidth: 0, margin: 0, fontSize: "12px", lineHeight: 1.4, color: "var(--dsw-alias-state-error-primary)" },
			fieldError: { margin: 0, fontSize: "12px", lineHeight: 1.4, color: "var(--dsw-alias-state-error-primary)" },
			historyList: { maxHeight: "460px", overflow: "auto", borderTop: "1px solid var(--dsw-alias-border-l1)" },
			historyTable: { borderCollapse: "collapse", minWidth: "820px", width: "100%", fontSize: "12px", lineHeight: 1.4, color: "var(--dsw-alias-label-primary)" },
			historyCell: { borderBottom: "1px solid var(--dsw-alias-border-l1)", padding: "7px 10px", height: "34px", boxSizing: "border-box", textAlign: "left", whiteSpace: "nowrap", verticalAlign: "middle" },
			historyHead: { position: "sticky", top: 0, background: "var(--dsw-alias-bg-base)", fontWeight: 600, color: "var(--dsw-alias-label-secondary)" },
			historyLine: { fontSize: "12px", lineHeight: 1.5, color: "var(--dsw-alias-label-secondary)", margin: "2px 0" },
			disclosure: { cursor: "pointer", padding: "8px 0", boxSizing: "border-box", color: "var(--dsw-alias-label-primary)", outlineColor: "var(--dsw-alias-brand-primary)", fontSize: "13px" },
			// Settings policy card groups with strict desktop grid alignment
			policyCard: { background: "var(--dsw-alias-bg-layer-1)", border: "1px solid rgba(255, 255, 255, 0.12)", borderRadius: "8px", overflow: "hidden", marginBottom: "14px", boxSizing: "border-box" },
			policyCardHeader: { padding: "10px 14px", borderBottom: "1px solid rgba(255, 255, 255, 0.08)", background: "var(--dsw-alias-bg-layer-2)" },
			policyCardTitle: { fontSize: "13px", fontWeight: 600, margin: 0, color: "var(--dsw-alias-label-primary)" },
			settingRow: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", borderBottom: "1px solid rgba(255, 255, 255, 0.07)", minHeight: "48px", boxSizing: "border-box", transition: "background-color 0.15s ease" },
			settingInfo: { flex: 1, minWidth: 0, paddingRight: "16px" },
			settingLabel: { fontSize: "13px", fontWeight: 500, lineHeight: 1.4, color: "var(--dsw-alias-label-primary)", display: "block" },
			settingDesc: { fontSize: "12px", lineHeight: 1.4, color: "var(--dsw-alias-label-secondary)", marginTop: "2px" },
			settingControl: { display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "8px", flexShrink: 0 },
			modeNotice: { padding: "10px 14px", fontSize: "12px", lineHeight: 1.5, color: "var(--dsw-alias-label-secondary)", background: "var(--dsw-alias-bg-layer-2)", borderTop: "1px solid rgba(255, 255, 255, 0.08)", boxSizing: "border-box" },
			headerBadge: { display: "inline-flex", alignItems: "center", justifyContent: "center", gap: "5px", fontSize: "12px", height: "26px", padding: "0 10px", borderRadius: "6px", border: "1px solid rgba(255, 255, 255, 0.14)", background: "rgba(255, 255, 255, 0.05)", color: "var(--dsw-alias-label-secondary)", userSelect: "none", boxSizing: "border-box", flexShrink: 0 },
			headerBtn: { appearance: "none", display: "inline-flex", alignItems: "center", justifyContent: "center", gap: "4px", fontSize: "12px", fontWeight: 500, height: "26px", padding: "0 12px", borderRadius: "6px", border: "1px solid rgba(255, 255, 255, 0.14)", background: "rgba(255, 255, 255, 0.05)", color: "var(--dsw-alias-label-primary)", cursor: "pointer", outlineColor: "var(--dsw-alias-brand-primary)", boxSizing: "border-box", flexShrink: 0, transition: "all 0.15s ease" },
			// The `web_search` conversation row. The card body itself is DSH's own
			// WebBlock; these styles are only the row chrome around it.
			toolRow: { display: "grid", gap: "2px", margin: "4px 0", minWidth: 0 },
			toolHead: { appearance: "none", width: "100%", display: "flex", alignItems: "center", gap: "8px", minHeight: "30px", padding: "2px 6px", border: "none", borderRadius: "6px", background: "transparent", color: "var(--dsw-alias-label-primary)", font: "inherit", fontSize: "13px", textAlign: "left", cursor: "pointer", outlineColor: "var(--dsw-alias-brand-primary)", boxSizing: "border-box" },
			toolHeadStatic: { cursor: "default" },
			toolIcon: { display: "inline-flex", alignItems: "center", flexShrink: 0, color: "var(--dsw-alias-label-secondary)" },
			toolName: { flexShrink: 0, fontWeight: 500, color: "var(--dsw-alias-label-primary)" },
			toolQuery: { flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "var(--dsw-alias-label-secondary)" },
			toolStatus: { flexShrink: 0, fontSize: "12px", color: "var(--dsw-alias-label-secondary)" },
			toolBody: { minWidth: 0, padding: "4px 6px 6px", display: "grid", gap: "8px" },
			toolAnswer: { margin: 0, fontSize: "13px", lineHeight: 1.6, color: "var(--dsw-alias-label-primary)", whiteSpace: "pre-wrap", overflowWrap: "anywhere" },
			toolRaw: { margin: 0, maxHeight: "240px", overflow: "auto", fontSize: "12px", lineHeight: 1.5, fontFamily: "ui-monospace, monospace", color: "var(--dsw-alias-label-secondary)", whiteSpace: "pre-wrap", wordBreak: "break-word" },
			toolList: { margin: 0, padding: "0 0 0 1.2em", display: "grid", gap: "8px" },
			toolItem: { display: "grid", gap: "2px", minWidth: 0 },
			toolLink: { fontSize: "13px", lineHeight: 1.4, color: "var(--dsw-alias-brand-primary)", textDecoration: "none", overflowWrap: "anywhere" },
			toolSnippet: { margin: 0, fontSize: "12px", lineHeight: 1.5, color: "var(--dsw-alias-label-secondary)", overflowWrap: "anywhere" },
		};

		/** Modern PC desktop switch component */
		function Switch({ id, checked, disabled, onChange }) {
			return h("button", {
				id,
				type: "button",
				role: "switch",
				className: "aws-switch",
				"aria-checked": checked,
				disabled,
				style: {
					position: "relative",
					display: "inline-flex",
					alignItems: "center",
					width: "36px",
					height: "20px",
					borderRadius: "10px",
					border: "1px solid var(--dsw-alias-border-l2)",
					padding: "1px",
					background: checked ? "var(--dsw-alias-brand-primary)" : "var(--dsw-alias-bg-layer-2)",
					cursor: disabled ? "default" : "pointer",
					transition: "background-color 0.2s ease, border-color 0.2s ease",
					outlineColor: "var(--dsw-alias-brand-primary)",
					flexShrink: 0,
					opacity: disabled ? 0.45 : 1,
					boxSizing: "border-box",
				},
				onClick: () => onChange(!checked),
			},
				h("span", {
					style: {
						width: "16px",
						height: "16px",
						borderRadius: "50%",
						background: checked ? "var(--dsw-alias-bg-base)" : "var(--dsw-alias-label-secondary)",
						transform: checked ? "translateX(16px)" : "translateX(0px)",
						transition: "transform 0.2s ease, background-color 0.2s ease",
						display: "block",
						boxShadow: "0 1px 2px rgba(0, 0, 0, 0.25)",
					}
				})
			);
		}

		/** Password field with togglable visibility for PC desktop convenience */
		function PasswordInput({ value, placeholder, disabled, onChange, style }) {
			const [show, setShow] = React.useState(false);
			return h("div", { style: { position: "relative", width: "100%", minWidth: 0 } },
				h("input", {
					type: show ? "text" : "password",
					className: "aws-input",
					style: {
						...styles.input,
						width: "100%",
						paddingRight: "30px",
						boxSizing: "border-box",
						...style,
					},
					placeholder,
					value: value ?? "",
					disabled,
					spellCheck: false,
					autoComplete: "off",
					onChange: (event) => onChange(event.target.value),
				}),
				h("button", {
					type: "button",
					className: "aws-icon-btn",
					style: {
						position: "absolute",
						right: "4px",
						top: "50%",
						transform: "translateY(-50%)",
						background: "transparent",
						border: "none",
						cursor: disabled ? "default" : "pointer",
						padding: "3px",
						display: "inline-flex",
						alignItems: "center",
						justifyContent: "center",
						color: "var(--dsw-alias-label-secondary)",
						opacity: disabled ? 0.3 : 0.65,
						borderRadius: "4px",
					},
					disabled,
					title: show ? "隐藏密码" : "显示密码",
					onClick: () => setShow(!show),
				}, h(show ? IconEyeOff : IconEye, { size: 14 }))
			);
		}

		/** One scalar text/number input row aligned cleanly in card table */
		function ScalarRow(props) {
			const { t, id, label, description, field, numeric, disabled } = props;
			const invalid = Object.hasOwn(props, "invalid") ? props.invalid : false;
			const [hovered, setHovered] = React.useState(false);
			const base = numeric ? styles.inputNum : styles.input;

			return h("div", {
				className: "aws-interactive-row",
				style: {
					...styles.settingRow,
					background: hovered ? "var(--dsw-alias-bg-layer-2)" : "transparent",
				},
				onMouseEnter: () => setHovered(true),
				onMouseLeave: () => setHovered(false),
			},
				h("div", { style: styles.settingInfo },
					h("label", { className: "aws-row-title", style: styles.settingLabel, htmlFor: id }, label),
					description ? h("div", { style: styles.settingDesc }, description) : null,
					invalid ? h("div", { style: { ...styles.fieldError, marginTop: "2px" } }, t("invalidNumber")) : null,
				),
				h("div", { style: styles.settingControl },
					h("input", {
						id,
						type: "text",
						className: "aws-input",
						inputMode: numeric ? "numeric" : undefined,
						style: invalid
							? { ...base, borderColor: "var(--dsw-alias-state-error-primary)" }
							: disabled ? { ...base, ...DISABLED_TEXT } : base,
						value: field.text,
						disabled,
						"aria-invalid": invalid ? "true" : undefined,
						spellCheck: false,
						onChange: (event) => { props.onEdit(event.target.value); },
					}),
					field.overridden
						? h("button", {
							type: "button",
							className: "aws-icon-btn",
							style: {
								...styles.iconBtn,
								opacity: hovered ? 1 : 0.65,
								color: "var(--dsw-alias-brand-primary)",
							},
							title: t("reset"),
							disabled,
							onClick: props.onReset,
						}, h(IconReset, { size: 13 }))
						: h("span", { style: { width: "26px", flexShrink: 0 } }),
				),
			);
		}

		/** One toggle row aligned cleanly in card table */
		function BooleanRow(props) {
			const { t, id, label, description, field, disabled } = props;
			const [hovered, setHovered] = React.useState(false);
			const isChecked = field.text === "true";

			return h("div", {
				className: "aws-interactive-row",
				style: {
					...styles.settingRow,
					background: hovered ? "var(--dsw-alias-bg-layer-2)" : "transparent",
					cursor: disabled ? "default" : "pointer",
				},
				onMouseEnter: () => setHovered(true),
				onMouseLeave: () => setHovered(false),
				onClick: (e) => {
					if (!disabled && e.target.tagName !== "BUTTON" && !e.target.closest("button")) {
						props.onEdit(isChecked ? "false" : "true");
					}
				},
			},
				h("div", { style: styles.settingInfo },
					h("label", { className: "aws-row-title", style: { ...styles.settingLabel, cursor: disabled ? "default" : "pointer" }, htmlFor: id }, label),
					description ? h("div", { style: styles.settingDesc }, description) : null,
				),
				h("div", { style: styles.settingControl, onClick: (e) => e.stopPropagation() },
					h(Switch, {
						id,
						checked: isChecked,
						disabled,
						onChange: (next) => props.onEdit(next ? "true" : "false"),
					}),
					field.overridden
						? h("button", {
							type: "button",
							className: "aws-icon-btn",
							style: {
								...styles.iconBtn,
								opacity: hovered ? 1 : 0.65,
								color: "var(--dsw-alias-brand-primary)",
							},
							title: t("reset"),
							disabled,
							onClick: props.onReset,
						}, h(IconReset, { size: 13 }))
						: h("span", { style: { width: "26px", flexShrink: 0 } }),
				),
			);
		}

		/** A source row with compact, hover-only action icon and card-like config panel */
		function UpstreamRow(props) {
			const { t, entry, availability, disabled } = props;
			const [open, setOpen] = React.useState(false);
			const [hovered, setHovered] = React.useState(false);
			const state = availability[entry.kind] ?? { state: "unset" };
			const ref = KIND_CREDENTIAL_REF[entry.kind];
			const isAnon = state.state === "anonymous";
			const isConfigured = state.state === "configured";
			const badgeStyle = isAnon ? styles.badgeAnon : isConfigured ? styles.badgeOk : styles.badge;
			const dotColor = isAnon ? "rgb(14, 165, 233)" : isConfigured ? "var(--dsw-alias-state-success-primary)" : "var(--dsw-alias-label-secondary)";
			const keyLabel = isAnon ? t("keyAnonymous") : isConfigured ? t("keyConfigured") : t("keyUnset");

			return h("div", {
				style: styles.entry,
				onMouseEnter: () => setHovered(true),
				onMouseLeave: () => setHovered(false),
			},
				h("div", {
					className: "aws-interactive-row",
					style: {
						...styles.settingRow,
						background: hovered ? "var(--dsw-alias-bg-layer-2)" : "transparent",
						cursor: "pointer",
						borderBottom: open ? "1px solid var(--dsw-alias-border-l1)" : "none",
					},
					onClick: (event) => {
						// Clicking the row (outside the checkbox) toggles expand
						if (event.target.tagName !== "INPUT" && event.target.tagName !== "BUTTON" && !event.target.closest("button")) {
							setOpen(!open);
						}
					},
				},
					h("div", {
						style: { display: "flex", alignItems: "center", gap: "10px", minWidth: 0, flex: 1 },
					},
						h("input", {
							type: "checkbox",
							className: "aws-checkbox",
							checked: entry.enabled,
							disabled,
							style: { cursor: disabled ? "default" : "pointer" },
							onClick: (e) => e.stopPropagation(),
							onChange: event => props.onToggle(event.target.checked),
						}),
						h("span", {
							className: "aws-row-title",
							style: { ...styles.entryName, cursor: "pointer", userSelect: "none" },
							onClick: () => setOpen(!open),
						}, KIND_LABEL[entry.kind]),
					),
					h("div", {
						style: { display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 },
						onClick: (e) => e.stopPropagation(),
					},
						h("button", {
							type: "button",
							className: "aws-icon-btn",
							style: {
								...styles.iconBtn,
								opacity: (hovered || open) ? 1 : 0,
								pointerEvents: (hovered || open) ? "auto" : "none",
								...(open ? styles.iconBtnActive : {}),
							},
							title: open ? t("collapse") : t("configure"),
							"aria-expanded": open,
							"aria-controls": `aws-source-${entry.kind}`,
							onClick: () => setOpen(!open),
						}, h(IconSettings, { size: 14, color: open ? "var(--dsw-alias-brand-primary)" : undefined })),
						h("span", { style: badgeStyle },
							h(StatusDot, { color: dotColor }),
							keyLabel,
						),
					),
				),
				open ? h("div", { id: `aws-source-${entry.kind}`, style: { ...styles.panel, margin: "8px 14px 12px" } },
					ENDPOINT_OVERRIDE_KINDS.includes(entry.kind) ? h("label", { style: { display: "block" } },
						h("span", { style: styles.label }, t("endpoint")),
						h("input", {
							type: "url",
							style: { ...styles.input, width: "100%", display: "block", marginTop: "4px" },
							placeholder: KIND_DEFAULT_BASE_URL[entry.kind],
							value: entry.baseURL,
							disabled,
							spellCheck: false,
							onChange: event => props.onBaseURL(event.target.value),
						}),
					) : null,
					ENDPOINT_OVERRIDE_KINDS.includes(entry.kind)
						? h("p", { style: { ...styles.hint, margin: "2px 0 4px" } }, t("endpointHint"))
						: null,
					MODEL_ENV[entry.kind] ? h("label", { style: { display: "block", marginTop: "4px" } },
						h("span", { style: styles.label }, t("model")),
						h("input", {
							type: "text",
							style: { ...styles.input, width: "100%", display: "block", marginTop: "4px" },
							placeholder: KIND_DEFAULT_MODELS[entry.kind] ?? "",
							value: entry.models ?? "",
							disabled,
							spellCheck: false,
							onChange: event => props.onModels(event.target.value),
						}),
						h("p", { style: { ...styles.hint, margin: "2px 0 4px" } }, t("modelHint")),
					) : null,
					TOOL_TYPE_KINDS.includes(entry.kind) ? h("label", { style: { display: "block", marginTop: "4px" } },
						h("span", { style: styles.label }, t("toolType")),
						h("input", {
							type: "text",
							style: { ...styles.input, width: "100%", display: "block", marginTop: "4px" },
							placeholder: KIND_DEFAULT_TOOL_TYPE[entry.kind] ?? "",
							value: entry.toolType ?? "",
							disabled,
							spellCheck: false,
							onChange: event => props.onToolType(event.target.value),
						}),
						h("p", { style: { ...styles.hint, margin: "2px 0 4px" } }, t("toolTypeHint")),
					) : null,
					TOOL_NAME_KINDS.includes(entry.kind) ? h("label", { style: { display: "block", marginTop: "4px" } },
						h("span", { style: styles.label }, t("toolName")),
						h("input", {
							type: "text",
							style: { ...styles.input, width: "100%", display: "block", marginTop: "4px" },
							placeholder: "web_search",
							value: entry.toolName ?? "",
							disabled,
							spellCheck: false,
							onChange: event => props.onToolName(event.target.value),
						}),
						h("p", { style: { ...styles.hint, margin: "2px 0 4px" } }, t("toolNameHint")),
					) : null,
					ref === null ? null : h("label", { style: { display: "block" } },
						h("span", { style: styles.label }, t("key")),
						h("div", { style: { marginTop: "4px" } },
							h(PasswordInput, {
								placeholder: isConfigured ? t("keyPlaceholderConfigured") : t("keyPlaceholder"),
								value: entry.draft,
								disabled: disabled || state.writable === false,
								onChange: text => props.onKey(text),
							}),
						),
					),
				) : null,
			);
		}

		/** Read-only, process-local diagnostics from Connection's authenticated fetch route. */
		function SearchHistoryPanel({ t }) {
			const [state, setState] = React.useState({ entries: [], selectedProvider: null, loading: true, error: false });
			React.useEffect(() => {
				let active = true;
				const refresh = async () => {
					try {
						const response = await fetch("/api/agent-web-search/history", { credentials: "same-origin", cache: "no-store" });
						if (!response.ok) throw new Error("history unavailable");
						const body = await response.json();
						if (!Array.isArray(body?.entries)) throw new Error("invalid history");
						if (active) setState({ entries: body.entries, selectedProvider: body.selectedProvider ?? null, loading: false, error: false });
					} catch {
						if (active) setState((old) => ({ ...old, loading: false, error: true }));
					}
				};
				void refresh();
				const timer = setInterval(() => { void refresh(); }, 5000);
				return () => { active = false; clearInterval(timer); };
			}, []);

			const handleWheel = (e) => {
				if (e.deltaY !== 0 && e.currentTarget) {
					e.currentTarget.scrollLeft += e.deltaY;
				}
			};

			return h("div", { style: styles.section },
				h("div", { style: styles.policyCard },
					h("div", { style: styles.policyCardHeader },
						h("h4", { style: styles.policyCardTitle }, t("history")),
					),
					!state.error && state.selectedProvider && state.selectedProvider !== "agent-web-search"
						? h("div", { style: { padding: "8px 14px", background: "rgba(239, 68, 68, 0.08)", borderBottom: "1px solid var(--dsw-alias-border-l1)" } },
							h("p", { style: { ...styles.fieldError, margin: 0 } }, t("notSelected")),
						)
						: null,
					state.error ? h("div", { style: { padding: "10px 14px" } }, h("p", { style: { ...styles.fieldError, margin: 0 } }, t("historyError"))) : null,
					h("div", {
						style: styles.historyList,
						role: "region",
						"aria-label": t("history"),
						tabIndex: 0,
						onWheel: handleWheel,
					},
						h("table", { style: styles.historyTable },
							h("thead", null, h("tr", null,
								[["historyTime", "160px"], ["historyState", "70px"], ["historyMode", "68px"], ["historyTotal", "145px"], ["historyAttempts", "auto"]].map(([name, width]) => h("th", { key: name, scope: "col", style: { ...styles.historyCell, ...styles.historyHead, width } }, t(name))),
							)),
							h("tbody", null,
								state.entries.map((entry) => {
									const date = new Date(entry.at);
									const stamp = Number.isNaN(date.getTime()) ? entry.at : date.toLocaleString();
									const status = entry.status === "success" ? t("historySuccess") : entry.status === "aborted" ? t("historyAborted") : t("historyFailed");
									const attempts = (entry.attempts ?? []).map(attempt =>
										`${KIND_LABEL[attempt.kind] ?? attempt.kind}${attempt.sourceId ? ` (${attempt.sourceId})` : ""}: ${t(`historyStatus_${attempt.status}`)} ${attempt.resultCount} ${t("resultUnit")}, ${attempt.durationMs} ms${attempt.httpStatus ? `, HTTP ${attempt.httpStatus}` : ""}`
									).join("  |  ");
									return h("tr", { key: entry.id },
										h("td", { style: styles.historyCell }, stamp),
										h("td", { style: { ...styles.historyCell, color: entry.status === "success" ? "var(--dsw-alias-state-success-primary)" : "var(--dsw-alias-state-error-primary)" } }, status),
										h("td", { style: styles.historyCell }, t(entry.mode === "fallback" ? "fallbackShort" : "fanoutShort")),
										h("td", { style: styles.historyCell }, `${entry.resultCount} ${t("resultUnit")} · ${entry.durationMs} ms`),
										h("td", { style: styles.historyCell, title: attempts }, attempts),
									);
								}),
								!state.error && state.loading && state.entries.length === 0
									? h("tr", { key: "loading" },
										h("td", { colSpan: 5, style: { ...styles.historyCell, textAlign: "center", padding: "28px 14px", color: "var(--dsw-alias-label-secondary)" } }, t("loading")),
									)
									: null,
								!state.error && !state.loading && state.entries.length === 0
									? h("tr", { key: "empty" },
										h("td", { colSpan: 5, style: { ...styles.historyCell, textAlign: "center", padding: "32px 14px", color: "var(--dsw-alias-label-secondary)" } }, t("historyEmpty")),
									)
									: null,
							),
						),
					),
					h("div", { style: styles.modeNotice }, t("historyHint")),
				),
			);
		}

		/** A single settings.section page with progressive, native-style sub-navigation. */
		function AgentWebSearchCard(props) {
			ensureInteractiveStyles();
			const { t } = props;
			const [tab, setTab] = React.useState("sources");
			const state = props.useAgentWebSearch((snapshot) => snapshot);
			if (!state.available) return h("p", { style: styles.notice }, state.status === "loading" ? t("loading") : t("unavailable"));
			const disabled = !state.writable;
			const enabledCount = state.queue.filter(entry => entry.enabled).length;
			const showActions = state.dirty || state.saving || state.failed;

			return h("div", { style: styles.page },
				h("div", { style: styles.header },
					h("h2", { style: styles.pageTitle }, t("title")),
				),
				h("nav", { style: styles.tabs, "aria-label": t("title") },
					[["sources", "tabSources"], ["policy", "tabPolicy"], ["activity", "tabActivity"]].map(([id, label]) => h("button", { key: id, type: "button", className: "aws-tab", style: { ...styles.tab, ...(tab === id ? styles.tabActive : {}) }, "aria-current": tab === id ? "page" : undefined, onClick: () => setTab(id) }, t(label))),
				),
				tab === "sources" ? h("section", { style: styles.section },
					h("div", { style: styles.policyCard },
						h("div", { style: { ...styles.policyCardHeader, display: "flex", alignItems: "center", justifyContent: "space-between" } },
							h("h4", { style: styles.policyCardTitle }, t("upstreams")),
							h("span", { style: styles.headerBadge }, `${enabledCount} / ${state.queue.length} ${t("enabled")}`),
						),
						state.queue.map(entry => h(UpstreamRow, {
							key: entry.kind, t, entry, availability: state.availability, disabled,
							onToggle: enabled => props.setEnabled(entry.kind, enabled), onBaseURL: text => props.setBaseURL(entry.kind, text), onModels: text => props.setModels(entry.kind, text), onToolType: text => props.setToolType(entry.kind, text), onToolName: text => props.setToolName(entry.kind, text), onKey: text => props.setKeyDraft(entry.kind, text)
						})),
						h("div", { style: styles.modeNotice }, t("upstreamsHint")),
					),
				) : null,
				tab === "policy" ? h("section", { style: styles.section },
					// Card 1: Dispatch mode
					h("div", { style: styles.policyCard },
						h("div", { style: styles.policyCardHeader },
							h("h4", { style: styles.policyCardTitle }, t("mode")),
						),
						h("div", { style: styles.settingRow },
							h("div", { style: styles.settingInfo },
								h("label", { style: styles.settingLabel, htmlFor: "aws-mode" }, t("policyModeTitle")),
								h("div", { style: styles.settingDesc }, t("policyModeDesc")),
							),
							h("div", { style: styles.settingControl },
								h("select", {
									id: "aws-mode",
									style: { ...styles.select, width: "180px" },
									value: state.mode.text || "fanout",
									disabled,
									onChange: event => props.edit("mode", event.target.value),
								},
									h("option", { value: "fanout" }, t("modeFanout")),
									h("option", { value: "fallback" }, t("modeFallback")),
								),
								state.mode.overridden
									? h("button", {
										type: "button",
										style: { ...styles.iconBtn, color: "var(--dsw-alias-brand-primary)" },
										title: t("reset"),
										disabled,
										onClick: () => props.resetField("mode"),
									}, h(IconReset, { size: 13 }))
									: h("span", { style: { width: "26px", flexShrink: 0 } }),
							),
						),
						h("div", { style: styles.modeNotice }, t("modeHint")),
					),

					// Card 2: timeouts. `max_results` is intentionally absent: it is a
					// per-call request input in the core contract, not a DSH setting.
					h("div", { style: styles.policyCard },
						h("div", { style: styles.policyCardHeader },
							h("h4", { style: styles.policyCardTitle }, t("limitsGroup")),
						),
						h(ScalarRow, {
							key: "attemptTimeoutMs", t, id: "aws-attemptTimeoutMs",
							label: t("attemptTimeout"), description: t("attemptTimeoutDesc"),
							field: state.attemptTimeoutMs, numeric: true, disabled,
							invalid: state.invalid === "attemptTimeoutMs",
							onEdit: text => props.edit("attemptTimeoutMs", text),
							onReset: () => props.resetField("attemptTimeoutMs"),
						}),
						h(ScalarRow, {
							key: "totalTimeoutMs", t, id: "aws-totalTimeoutMs",
							label: t("totalTimeout"), description: t("totalTimeoutDesc"),
							field: state.totalTimeoutMs, numeric: true, disabled,
							invalid: state.invalid === "totalTimeoutMs",
							onEdit: text => props.edit("totalTimeoutMs", text),
							onReset: () => props.resetField("totalTimeoutMs"),
						}),
					),

					// Card 3: Boolean options
					h("div", { style: styles.policyCard },
						h("div", { style: styles.policyCardHeader },
							h("h4", { style: styles.policyCardTitle }, t("filterGroup")),
						),
						h(BooleanRow, {
							t, id: "aws-dedupe",
							label: t("dedupeByUrl"), description: t("dedupeByUrlDesc"),
							field: state.dedupeByUrl, disabled,
							onEdit: text => props.edit("dedupeByUrl", text),
							onReset: () => props.resetField("dedupeByUrl"),
						}),
						h(BooleanRow, {
							t, id: "aws-answer",
							label: t("includeAnswer"), description: t("includeAnswerDesc"),
							field: state.includeAnswer, disabled,
							onEdit: text => props.edit("includeAnswer", text),
							onReset: () => props.resetField("includeAnswer"),
						}),
					),
				) : null,
				tab === "activity" ? h(SearchHistoryPanel, { t }) : null,

				// Only render the floating action bar when there are unsaved changes or errors, avoiding blocking UI
				showActions ? h("div", { style: styles.floatingBar },
					h("div", { style: { display: "flex", alignItems: "center", gap: "8px", minWidth: 0, flex: 1 } },
						state.invalid
							? h("div", { style: { display: "flex", alignItems: "center", gap: "6px", color: "var(--dsw-alias-state-error-primary)" } },
								h(IconAlert, { size: 15, color: "var(--dsw-alias-state-error-primary)" }),
								h("span", { style: styles.fieldError }, t("invalidNumber")),
							)
							: state.failed
								? h("div", { style: { display: "flex", alignItems: "center", gap: "6px", color: "var(--dsw-alias-state-error-primary)" } },
									h(IconAlert, { size: 15, color: "var(--dsw-alias-state-error-primary)" }),
									h("span", { style: styles.fieldError }, t("saveFailed")),
								)
								: h("div", { style: { display: "flex", alignItems: "center", gap: "6px" } },
									h(StatusDot, { color: "var(--dsw-alias-brand-primary)" }),
									h("span", { style: { fontSize: "13px", color: "var(--dsw-alias-label-secondary)" } }, t("notSaved")),
								),
					),
					h("div", { style: { display: "flex", alignItems: "center", gap: "8px" } },
						disabled ? h("span", { style: styles.badge }, t("readOnly")) : null,
						h("button", {
							type: "button",
							className: "aws-btn",
							style: styles.button,
							disabled: disabled || state.saving || !state.dirty,
							onClick: props.discard,
						}, t("discard")),
						h("button", {
							type: "button",
							className: "aws-btn-primary",
							style: styles.buttonPrimary,
							disabled: disabled || state.saving || !state.dirty || !!state.invalid,
							onClick: props.save,
						}, state.saving ? t("saving") : t("save")),
					),
				) : null,
			);
		}
		//#endregion

		//#region web_search conversation row
		/**
		 * DSH's own web card, when this bundle can reach it.
		 *
		 * Reusing the shipped `WebBlock` keeps the citation list identical to the
		 * built-in row instead of approximating it. The guard matters: a client module
		 * that is not registered must not take the whole client half down with it.
		 */
		let webCardParts = null;
		try {
			const primitives = require("@deepseek-ai/dsh-client-ui-primitives");
			// A React element type is a function or a host tag; both are renderable.
			const renderable = value => typeof value === "function" || typeof value === "string";
			if (primitives !== null && typeof primitives === "object" && renderable(primitives.WebBlock)) {
				webCardParts = {
					WebBlock: primitives.WebBlock,
					Icon: renderable(primitives.IconGlobeOutlineRegular) ? primitives.IconGlobeOutlineRegular : null,
				};
			}
		} catch {
			webCardParts = null;
		}

		/** Parse one tool call's recorded arguments, or null when they are unusable. */
		function toolArguments(raw) {
			if (typeof raw !== "string" || raw.trim() === "") return null;
			try {
				const value = JSON.parse(raw);
				return typeof value === "object" && value !== null && !Array.isArray(value) ? value : null;
			} catch {
				return null;
			}
		}

		/** A settled result's text, for the cases a card cannot render. */
		function resultText(block) {
			if (!Array.isArray(block?.content)) return "";
			return block.content
				.filter(part => part !== null && typeof part === "object" && part.type === "text" && typeof part.text === "string")
				.map(part => part.text)
				.join("\n");
		}

		/** The card data our Host half persisted, or null when there is none. */
		function webCard(block) {
			const meta = block?.meta;
			if (typeof meta !== "object" || meta === null || Array.isArray(meta)) return null;
			if (!Array.isArray(meta.sources)) return null;
			return {
				answer: typeof meta.answer === "string" && meta.answer !== "" ? meta.answer : undefined,
				sources: meta.sources
					.filter(source => source !== null && typeof source === "object" && typeof source.url === "string")
					.map(source => ({
						url: source.url,
						...(typeof source.title === "string" ? { title: source.title } : {}),
						...(typeof source.snippet === "string" ? { snippet: source.snippet } : {}),
						...(typeof source.publishedAt === "string" ? { publishedAt: source.publishedAt } : {}),
					})),
				truncated: meta.truncated === true,
			};
		}

		/**
		 * The `web_search` conversation row.
		 *
		 * The plugin deliberately registers the MCP operation's argument shape
		 * (`query`), but the shipped row only builds a citation card when a call
		 * carries its own `{ queries }` array, so it declines and the conversation
		 * falls back to the raw result text. Claiming this keyed view is the
		 * supported way back — the slot contract says to "register at a different
		 * priority to shadow it (lowest renders)", and -1 beats the shipped 0.
		 * Every path below degrades to the same raw text the shipped row would have
		 * shown, so nothing renders worse than before.
		 */
		function WebSearchRow(props) {
			const { t, block, useDisclosure } = props;
			const settled = typeof block === "object" && block !== null && "kind" in block;
			const running = !settled;
			// Arguments live on the call head once the call is dispatched, and on the
			// block itself while it is still starting.
			const args = toolArguments(settled ? block.call?.argsRaw : block?.argsRaw);
			const query = typeof args?.query === "string" ? args.query : "";
			const failed = settled && block.isError === true;
			const card = settled && !failed ? webCard(block) : null;
			const text = settled && !failed ? resultText(block) : "";
			const failure = failed
				? (typeof block.error?.message === "string" && block.error.message !== "" ? block.error.message : resultText(block))
				: "";
			const raw = failure !== "" ? failure : text;
			const { expanded, toggle } = useDisclosure();
			const expandable = !running && (card !== null || raw !== "");
			const open = expanded && expandable;
			const status = running
				? t("cardRunning")
				: failed
					? t("cardFailed")
					: card === null
						? ""
						: card.sources.length === 0 && card.answer === undefined
							? t("cardEmpty")
							: `${card.sources.length} ${t("resultUnit")}`;
			// `answer` stays out of WebBlock so the search body never needs the
			// conversation namespace's markdown label bundle; we render it above.
			const labels = { noResults: t("cardEmpty"), sourcesTruncated: t("cardTruncated"), markdown: undefined };
			return h("div", { style: styles.toolRow },
				h("button", {
					type: "button",
					style: expandable ? styles.toolHead : { ...styles.toolHead, ...styles.toolHeadStatic },
					onClick: expandable ? toggle : undefined,
					"aria-expanded": expandable ? open : undefined,
				},
					h("span", { style: styles.toolIcon }, webCardParts?.Icon ? h(webCardParts.Icon, { size: 14 }) : null),
					h("span", { style: styles.toolName }, t("cardTitle")),
					query === "" ? null : h("span", { style: styles.toolQuery }, query),
					status === "" ? null : h("span", { style: styles.toolStatus }, status),
				),
				open ? h("div", { style: styles.toolBody },
					card !== null && card.answer !== undefined ? h("p", { style: styles.toolAnswer }, card.answer) : null,
					card === null ? null : webCardParts !== null
						? h(webCardParts.WebBlock, { kind: "search", sources: card.sources, truncated: card.truncated, labels })
						: h("ol", { style: styles.toolList },
							card.sources.map((source, index) => h("li", { key: `${index}:${source.url}`, style: styles.toolItem },
								h("a", { href: source.url, target: "_blank", rel: "noreferrer", style: styles.toolLink },
									typeof source.title === "string" && source.title !== "" ? source.title : source.url),
								typeof source.snippet === "string" && source.snippet !== "" ? h("p", { style: styles.toolSnippet }, source.snippet) : null,
							)),
						),
					card === null && raw !== "" ? h("pre", { style: styles.toolRaw }, raw) : null,
				) : null,
			);
		}
		//#endregion

		//#region entry
		/** Required services (cordis fiber inject). */
		const inject = ["slots", "locale", "remote", "remote.credentials", "configForms"];

		/** Mount the one settings.section page while its Host namespace is served. */
		function apply(ctx) {
			const t = ctx.locale.bind(NS);
			ctx.effect(() => ctx.locale.register(NS, { zh, en }), "agent-web-search: dictionaries");
			const controller = new CardController(ctx.configForms.get(NS), ctx);
			ctx.effect(() => () => { controller.dispose(); }, "agent-web-search: form subscription");
			ctx.effect(() => ctx.remote.$on("credentials/reference-updated", () => {
				controller.readCredentials();
			}), "agent-web-search: credential invalidations");
			ctx.effect(() => {
				// The shipped web row keeps key `web_search` at the default priority, and
				// re-registering the same key at the same priority throws instead of
				// replacing — the ledger says to "register at a different priority to
				// shadow it (lowest renders)". -1 wins over the shipped 0 regardless of
				// which side registers first.
				const offRow = ctx.slots.inject("tool.call.toolview", () => ctx.slots.register({
					name: "tool.call.toolview",
					key: "web_search",
					priority: -1,
					locale: NS,
				}, WebSearchRow));
				return () => { offRow(); };
			}, "agent-web-search: web_search citation row");
			ctx.effect(() => ctx.configForms.whileServed([NS], () => {
				const offSection = ctx.slots.inject("settings.section", () => ctx.slots.register({
					name: "settings.section",
					id: NS,
					// A thunk, not a string: the owner re-reads it on every projection,
					// so the nav label follows the active locale without re-registering.
					label: () => t("title"),
					order: 100,
					locale: NS,
					inject: () => controller.inject(),
				}, AgentWebSearchCard));
				return () => { offSection(); };
			}), "agent-web-search: settings card");
			void t;
		}

		exports.NS = NS;
		exports.apply = apply;
		exports.inject = inject;
		return module.exports;
	}
});
