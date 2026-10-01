/**
 * Shared constants for `dsh-agent-web-search`.
 *
 * The Host side (config, engine, tool) reads this module directly. The browser
 * card (`client.js`) is loaded by the client module loader and cannot reach a
 * Host module, so it carries a hand-mirrored copy of these tables behind a
 * "mirrored from lib/defaults.js" comment. Keep the two in step: when a kind is
 * added, renamed, or relabelled here, update the mirror too.
 *
 * @module dsh-agent-web-search/defaults
 */

/** Ported provider kinds, in the order the settings card lists them. */
export const PROVIDER_KINDS = [
  'exa',
  'parallel',
  'ddgs',
  'brave',
  'tavily',
  'perplexity',
  'you',
  'gemini',
  'grok',
  'ark',
  'zhipu_web_search',
  'zhipu_chat_search',
  'deepseek',
  'messages',
  'responses',
  'codex_alpha',
]

/** Human labels for the card's selects. */
export const KIND_LABEL = {
  exa: 'Exa',
  parallel: 'Parallel',
  ddgs: 'DuckDuckGo',
  brave: 'Brave Search',
  tavily: 'Tavily',
  perplexity: 'Perplexity',
  you: 'You.com',
  gemini: 'Gemini (Google Search grounding)',
  grok: 'Grok',
  ark: 'Volcengine ARK',
  zhipu_web_search: 'Zhipu Web Search',
  zhipu_chat_search: 'Zhipu Chat Search',
  deepseek: 'DeepSeek',
  messages: 'Anthropic Messages (generic)',
  responses: 'OpenAI Responses (generic)',
  codex_alpha: 'Codex Alpha (experimental)',
}

/**
 * The single credential reference each kind reads.
 *
 * `null` means the kind has an anonymous path: Exa and Parallel fall back to
 * their free MCP endpoints when no key is present, and DDGS scrapes the public
 * DuckDuckGo HTML endpoint — all three work with no configuration at all.
 */
export const KIND_CREDENTIAL_REF = {
  exa: 'EXA_API_KEY',
  parallel: 'PARALLEL_API_KEY',
  ddgs: null,
  brave: 'BRAVE_SEARCH_API_KEY',
  tavily: 'TAVILY_API_KEY',
  perplexity: 'PERPLEXITY_API_KEY',
  you: 'YDC_API_KEY',
  gemini: 'GEMINI_API_KEY',
  grok: 'XAI_API_KEY',
  ark: 'ARK_API_KEY',
  zhipu_web_search: 'ZHIPU_WEB_SEARCH_API_KEY',
  zhipu_chat_search: 'ZHIPU_CHAT_SEARCH_API_KEY',
  deepseek: 'DEEPSEEK_API_KEY',
  messages: 'AGENT_WEB_SEARCH_MESSAGES_API_KEY',
  responses: 'AGENT_WEB_SEARCH_RESPONSES_API_KEY',
  codex_alpha: 'AGENT_WEB_SEARCH_CODEX_ALPHA_API_KEY',
}

/** Kinds that run without any credential at all. */
export const ANONYMOUS_KINDS = ['exa', 'parallel', 'ddgs']

/**
 * Kinds whose Python provider honours a per-source endpoint override.
 *
 * `ddgs` is deliberately absent: it drives the `ddgs` library directly and reads
 * no endpoint variable, so offering the card an endpoint field for it would only
 * collect a value nothing can apply. Keep this aligned with the variables the
 * bridge maps and with what each provider in `agent_web_search/providers` reads.
 */
export const ENDPOINT_OVERRIDE_KINDS = PROVIDER_KINDS.filter(kind => kind !== 'ddgs')

/** Default upstream endpoints, also used as the card's input placeholders. */
export const KIND_DEFAULT_BASE_URL = {
  exa: 'https://mcp.exa.ai/mcp',
  parallel: 'https://search.parallel.ai/mcp',
  brave: 'https://api.search.brave.com/res/v1/web/search',
  tavily: 'https://api.tavily.com/search',
  perplexity: 'https://api.perplexity.ai/search',
  you: 'https://ydc-index.io/v1/search',
  gemini: 'https://generativelanguage.googleapis.com/v1beta/interactions',
  grok: 'https://api.x.ai/v1/responses',
  ark: 'https://ark.cn-beijing.volces.com/api/v3/responses',
  zhipu_web_search: 'https://open.bigmodel.cn',
  zhipu_chat_search: 'https://open.bigmodel.cn',
  deepseek: 'https://api.deepseek.com',
  messages: 'https://api.anthropic.com',
  responses: 'https://api.openai.com/v1',
  // Codex Alpha has no default endpoint: the gateway URL must be configured.
  // This value is only the card's input placeholder, never a fallback.
  codex_alpha: 'https://gateway.example/v1/alpha/search',
}

/**
 * The environment variable each model-backed kind reads its model list from.
 *
 * Kinds absent here take no model setting: their backend is fixed. Values are
 * comma-separated model names, except `codex_alpha` which takes a single
 * model. Mirrors the Python providers' `*_MODELS` variables.
 */
export const MODEL_ENV = {
  deepseek: 'AGENT_WEB_SEARCH_DEEPSEEK_MODELS',
  gemini: 'AGENT_WEB_SEARCH_GEMINI_MODELS',
  grok: 'AGENT_WEB_SEARCH_GROK_MODELS',
  ark: 'AGENT_WEB_SEARCH_ARK_MODELS',
  zhipu_chat_search: 'AGENT_WEB_SEARCH_ZHIPU_CHAT_MODELS',
  messages: 'AGENT_WEB_SEARCH_MESSAGES_MODELS',
  responses: 'AGENT_WEB_SEARCH_RESPONSES_MODELS',
  codex_alpha: 'AGENT_WEB_SEARCH_CODEX_ALPHA_MODEL',
}

/**
 * The models a fresh deployment uses when the card's model field is blank.
 * Card input placeholders only; the Python backends own the real defaults.
 */
export const KIND_DEFAULT_MODELS = {
  deepseek: 'deepseek-v4-flash',
  gemini: 'gemini-3.7-flash',
  grok: 'grok-4.6',
  ark: 'glm-5-2-260617, doubao-seed-2-1-turbo-260628, deepseek-v4-flash-ga-260731',
  zhipu_chat_search: 'glm-5.3-flash',
  messages: 'claude-3-7-sonnet-20250219, claude-3-5-haiku-20241022',
  responses: 'gpt-5-mini',
  codex_alpha: 'gpt-5.6-luna',
}


/**
 * The shipped queue.
 *
 * Only the three keyless upstreams ship ENABLED. Everything else is present but
 * off, and that asymmetry is deliberate: an enabled upstream with no key fails
 * its attempt on every search, so a queue that ships them on makes "enabled"
 * mean "will probably fail" and the Settings page would advertise sixteen rows
 * as on while none of them can serve. Turning one on is one click once its
 * credential is set — the card keeps every kind listed even when the section
 * omits it.
 *
 * `messages` and `responses` ship off even for a keyed deployment: both call a
 * general-purpose chat/response model to answer a search, which is a different
 * bargain from a search API (cost and latency are both model-sized), so they are
 * opt-in rather than default.
 */
export const DEFAULT_QUEUE = [
  { kind: 'exa', enabled: true, baseURL: '' },
  { kind: 'parallel', enabled: true, baseURL: '' },
  { kind: 'ddgs', enabled: true, baseURL: '' },
  { kind: 'brave', enabled: false, baseURL: '' },
  { kind: 'tavily', enabled: false, baseURL: '' },
  { kind: 'perplexity', enabled: false, baseURL: '' },
  { kind: 'you', enabled: false, baseURL: '' },
  { kind: 'gemini', enabled: false, baseURL: '' },
  { kind: 'grok', enabled: false, baseURL: '' },
  { kind: 'ark', enabled: false, baseURL: '' },
  { kind: 'zhipu_web_search', enabled: false, baseURL: '' },
  { kind: 'zhipu_chat_search', enabled: false, baseURL: '' },
  { kind: 'deepseek', enabled: false, baseURL: '' },
  { kind: 'messages', enabled: false, baseURL: '' },
  { kind: 'responses', enabled: false, baseURL: '' },
  { kind: 'codex_alpha', enabled: false, baseURL: '' },
]

/** Aggregation modes. */
export const MODES = ['fanout', 'fallback']

/** Bounds shared by the schema and the card's validation. */
export const MIN_ATTEMPT_TIMEOUT_MS = 1000
export const MAX_ATTEMPT_TIMEOUT_MS = 60000
export const DEFAULT_ATTEMPT_TIMEOUT_MS = 12000
export const MIN_TOTAL_TIMEOUT_MS = 2000
export const MAX_TOTAL_TIMEOUT_MS = 180000
export const DEFAULT_TOTAL_TIMEOUT_MS = 30000
// No max-results constants here: `max_results` is a per-call request input
// (core default 5, range 1-20), owned by the core schema, not by DSH config.

/** The id this plugin registers its provider under in the `ctx.web` seam. */
export const AGENT_WEB_SEARCH_PROVIDER_ID = 'agent-web-search'

/** The settings namespace: the composition entry id the Host keys the section by. */
export const AGENT_WEB_SEARCH_NAMESPACE = 'agent-web-search'

/** The package name, spelled here so both halves stay self-contained. */
export const PACKAGE_NAME = 'dsh-agent-web-search'

/**
 * The version reported to the Python child as the MCP client version.
 *
 * Kept here so it is not an unexplained literal deep in the bridge. It must match
 * `version` in both `package.json` files; `defaults.test.js` asserts that, so a
 * version bump fails a test instead of silently drifting.
 */
export const PACKAGE_VERSION = '0.8.0'
