import { spawn as defaultSpawn } from 'node:child_process'

import { ENDPOINT_OVERRIDE_KINDS, PACKAGE_NAME, PACKAGE_VERSION } from './defaults.js'

const DEFAULT_COMMAND = 'agent-web-search-mcp'
const DEFAULT_PROTOCOL_VERSION = '2025-06-18'
const MAX_OUTPUT_BYTES = 1024 * 1024

const CREDENTIAL_ENV = {
  ark: 'ARK_API_KEY',
  brave: 'BRAVE_SEARCH_API_KEY',
  codex_alpha: 'AGENT_WEB_SEARCH_CODEX_ALPHA_API_KEY',
  deepseek: 'DEEPSEEK_API_KEY',
  exa: 'EXA_API_KEY',
  gemini: 'GEMINI_API_KEY',
  grok: 'XAI_API_KEY',
  messages: 'AGENT_WEB_SEARCH_MESSAGES_API_KEY',
  parallel: 'PARALLEL_API_KEY',
  perplexity: 'PERPLEXITY_API_KEY',
  responses: 'AGENT_WEB_SEARCH_RESPONSES_API_KEY',
  tavily: 'TAVILY_API_KEY',
  you: 'YDC_API_KEY',
  zhipu_web_search: 'ZHIPU_WEB_SEARCH_API_KEY',
  zhipu_chat_search: 'ZHIPU_CHAT_SEARCH_API_KEY',
}

// Every endpoint variable a DSH deployment may have exported, so an inherited
// value can be cleared before the child starts. Assignment is limited to
// ENDPOINT_OVERRIDE_KINDS: `ddgs` appears here only to be cleared, because its
// Python provider reads no endpoint variable at all.
const ENDPOINT_ENV = {
  ark: 'AGENT_WEB_SEARCH_ARK_ENDPOINT',
  brave: 'AGENT_WEB_SEARCH_BRAVE_ENDPOINT',
  codex_alpha: 'AGENT_WEB_SEARCH_CODEX_ALPHA_ENDPOINT',
  ddgs: 'AGENT_WEB_SEARCH_DDGS_ENDPOINT',
  exa: 'EXA_MCP_URL',
  gemini: 'AGENT_WEB_SEARCH_GEMINI_ENDPOINT',
  grok: 'AGENT_WEB_SEARCH_GROK_ENDPOINT',
  parallel: 'AGENT_WEB_SEARCH_PARALLEL_ENDPOINT',
  perplexity: 'AGENT_WEB_SEARCH_PERPLEXITY_ENDPOINT',
  tavily: 'AGENT_WEB_SEARCH_TAVILY_ENDPOINT',
  you: 'AGENT_WEB_SEARCH_YOU_ENDPOINT',
}

const BASE_URL_ENV = {
  deepseek: 'AGENT_WEB_SEARCH_DEEPSEEK_BASE_URL',
  messages: 'AGENT_WEB_SEARCH_MESSAGES_BASE_URL',
  responses: 'AGENT_WEB_SEARCH_RESPONSES_BASE_URL',
  zhipu_web_search: 'AGENT_WEB_SEARCH_ZHIPU_WEB_SEARCH_BASE_URL',
  zhipu_chat_search: 'AGENT_WEB_SEARCH_ZHIPU_CHAT_BASE_URL',
}

const EXTRA_ENDPOINT_ENV = [
  'AGENT_WEB_SEARCH_EXA_ENDPOINT',
  'AGENT_WEB_SEARCH_PARALLEL_MCP_URL',
]

// Native tool-type overrides for the generic Messages/Responses backends.
const TOOL_TYPE_ENV = {
  messages: 'AGENT_WEB_SEARCH_MESSAGES_TOOL_TYPE',
  responses: 'AGENT_WEB_SEARCH_RESPONSES_TOOL_TYPE',
}

// Native tool-name override for the generic Messages backend.
const TOOL_NAME_ENV = {
  messages: 'AGENT_WEB_SEARCH_MESSAGES_TOOL_NAME',
}

// The environment variable each model-backed kind reads its model list from.
// Kinds absent here take no model setting. Values are comma-separated model
// names, except `codex_alpha` which takes a single model.
const MODEL_ENV = {
  deepseek: 'AGENT_WEB_SEARCH_DEEPSEEK_MODELS',
  gemini: 'AGENT_WEB_SEARCH_GEMINI_MODELS',
  grok: 'AGENT_WEB_SEARCH_GROK_MODELS',
  ark: 'AGENT_WEB_SEARCH_ARK_MODELS',
  zhipu_chat_search: 'AGENT_WEB_SEARCH_ZHIPU_CHAT_MODELS',
  messages: 'AGENT_WEB_SEARCH_MESSAGES_MODELS',
  responses: 'AGENT_WEB_SEARCH_RESPONSES_MODELS',
  codex_alpha: 'AGENT_WEB_SEARCH_CODEX_ALPHA_MODEL',
}

function endpointValue(raw) {
  if (typeof raw !== 'string' || raw.trim() === '') return undefined
  let url
  try { url = new URL(raw.trim()) } catch { throw providerError('provider endpoint is invalid', 'configuration') }
  const loopback = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)
  if ((url.protocol !== 'https:' && !(url.protocol === 'http:' && loopback)) || url.username || url.password || url.hash) {
    throw providerError('provider endpoint must use HTTPS, or HTTP on loopback, without credentials or fragments', 'configuration')
  }
  return url.href
}

const providerError = (message, code = 'bridge_error', details = {}) => {
  const error = new Error(message)
  error.code = code
  Object.assign(error, details)
  return error
}

function abortError(message = 'search aborted') {
  const error = new Error(message)
  error.name = 'AbortError'
  error.code = 'cancelled'
  return error
}

function timeoutError() {
  const error = new Error('search timed out')
  error.name = 'TimeoutError'
  error.code = 'timeout'
  return error
}

function parseArgs(raw) {
  if (!raw) return []
  let parsed
  try { parsed = JSON.parse(raw) } catch { throw providerError('MCP command arguments are invalid', 'configuration') }
  if (!Array.isArray(parsed) || parsed.some(item => typeof item !== 'string')) {
    throw providerError('MCP command arguments must be a JSON array of strings', 'configuration')
  }
  return parsed
}

function readEnvironment(options = {}) {
  const environment = options.environment ?? process.env
  const command = options.command ?? environment.AGENT_WEB_SEARCH_MCP_COMMAND ?? DEFAULT_COMMAND
  const args = options.args ?? parseArgs(environment.AGENT_WEB_SEARCH_MCP_ARGS)
  if (typeof command !== 'string' || command.trim() === '') {
    throw providerError('AGENT_WEB_SEARCH_MCP_COMMAND must not be empty', 'configuration')
  }
  return { command: command.trim(), args }
}

function withAbort(signal, promise) {
  if (!signal) return promise
  if (signal.aborted) return Promise.reject(signal.reason ?? abortError())
  return new Promise((resolve, reject) => {
    const onAbort = () => reject(signal.reason ?? abortError())
    signal.addEventListener('abort', onAbort, { once: true })
    promise.then(resolve, reject).finally(() => signal.removeEventListener('abort', onAbort)).catch(() => {})
  })
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

/** Only expose safe navigable web URLs to DSH citation surfaces. */
export function isSafeSourceUrl(value) {
  if (typeof value !== 'string' || value.length === 0) return false
  try {
    const url = new URL(value)
    return (url.protocol === 'http:' || url.protocol === 'https:')
      && url.hostname.length > 0
      && url.username === ''
      && url.password === ''
      && url.hash === ''
  } catch {
    return false
  }
}

/**
 * Validate and preserve the shared Python/MCP success payload.
 *
 * The bridge runs one MCP child per DSH upstream, but the child still returns
 * the public `{ query, providers }` envelope. Do not flatten that envelope at
 * this boundary: the model-facing native tool must retain provider grouping and
 * the core field names. The DSH citation projection is built separately by the
 * engine after this validation step.
 */
function mapProviderPayload(payload, expectedProvider) {
  if (!isPlainObject(payload) || typeof payload.query !== 'string' || !isPlainObject(payload.providers)) {
    throw providerError('MCP result was malformed', 'malformed_result')
  }
  const providerNames = Object.keys(payload.providers)
  if (expectedProvider !== undefined && (
    providerNames.length !== 1 || providerNames[0] !== expectedProvider
  )) {
    throw providerError('MCP result contained an unexpected provider payload', 'malformed_result')
  }
  const providers = {}
  for (const [provider, value] of Object.entries(payload.providers)) {
    if (!isPlainObject(value) || !Array.isArray(value.results)) {
      throw providerError('MCP result contained an invalid provider response', 'malformed_result')
    }
    if (value.answer !== undefined && typeof value.answer !== 'string') {
      throw providerError('MCP result contained an invalid provider answer', 'malformed_result')
    }
    const results = []
    // No DSH-side truncation: the core already bounds result counts, and every
    // returned row belongs in the model-facing payload.
    //
    // A row whose URL is not a safe navigable web URL is *dropped*, never
    // thrown: it is untrusted upstream data, and letting one bad row fail the
    // whole provider would hand a compromised upstream a denial-of-service
    // lever over the entire search. Malformed *types* are still protocol bugs
    // and keep failing loudly.
    for (const row of value.results) {
      if (!isPlainObject(row)
        || typeof row.title !== 'string'
        || typeof row.url !== 'string'
        || typeof row.description !== 'string'
        || (row.published_at !== undefined && typeof row.published_at !== 'string')
        || (row.author !== undefined && typeof row.author !== 'string')) {
        throw providerError('MCP result contained an invalid search result', 'malformed_result')
      }
      if (!isSafeSourceUrl(row.url)) continue
      results.push({
        title: row.title,
        url: row.url,
        description: row.description,
        ...(row.published_at !== undefined ? { published_at: row.published_at } : {}),
        ...(row.author !== undefined ? { author: row.author } : {}),
      })
    }
    providers[provider] = {
      ...(typeof value.answer === 'string' && value.answer.length > 0 ? { answer: value.answer } : {}),
      results,
    }
  }
  return { query: payload.query, providers }
}

function publicProviderErrors(value) {
  if (!value || typeof value !== 'object') return {}
  return Object.fromEntries(Object.entries(value).filter(([name, message]) => (
    typeof name === 'string' && typeof message === 'string' && message.length <= 160
  )))
}

function parseToolEnvelope(envelope) {
  if (!envelope || typeof envelope !== 'object') throw providerError('MCP result was malformed', 'malformed_result')
  if (envelope.error) throw providerError('MCP tool call failed', 'tool_error')
  const result = envelope.result
  if (!result || typeof result !== 'object' || !Array.isArray(result.content)) {
    throw providerError('MCP result was malformed', 'malformed_result')
  }
  const text = result.content
    .filter(part => part?.type === 'text' && typeof part.text === 'string')
    .map(part => part.text)
    .join('\n')
  if (text.length > MAX_OUTPUT_BYTES) throw providerError('MCP result exceeds 1 MiB', 'output_limit')
  let payload
  try { payload = JSON.parse(text) } catch { throw providerError('MCP result was not valid JSON', 'malformed_result') }
  if (result.isError === true || payload?.error?.code === 'all_providers_failed') {
    const error = providerError('All configured search providers failed', payload?.error?.code ?? 'all_providers_failed')
    error.providerErrors = publicProviderErrors(payload?.error?.provider_errors)
    throw error
  }
  return payload
}

class StdioRpc {
  constructor(child, signal, maxBytes = MAX_OUTPUT_BYTES, lineMode = false) {
    this.child = child
    this.signal = signal
    this.maxBytes = maxBytes
    this.lineMode = lineMode
    // Raw bytes, never a decoded string: a multi-byte UTF-8 sequence can be
    // split across two `data` chunks, and decoding each chunk on its own would
    // turn both halves into U+FFFD. Frames are decoded only once complete.
    this.buffer = Buffer.alloc(0)
    this.bytes = 0
    this.pending = new Map()
    this.closed = false
    this.onData = chunk => this.#data(chunk)
    this.onError = () => this.#fail(providerError('MCP process failed', 'process_error'))
    this.onExit = () => this.#fail(providerError('MCP process exited before replying', 'process_error'))
    this.onAbort = () => this.#fail(this.signal.reason ?? abortError())
    child.stdout?.on('data', this.onData)
    child.stderr?.on('data', chunk => {
      this.bytes += Buffer.byteLength(chunk)
      if (this.bytes > this.maxBytes) this.#fail(providerError('MCP output exceeds 1 MiB', 'output_limit'))
    })
    child.on('error', this.onError)
    child.on('exit', this.onExit)
    signal?.addEventListener('abort', this.onAbort, { once: true })
    if (signal?.aborted) this.#fail(signal.reason ?? abortError())
  }

  #data(chunk) {
    if (this.closed) return
    const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)
    this.bytes += bytes.length
    if (this.bytes > this.maxBytes) return this.#fail(providerError('MCP output exceeds 1 MiB', 'output_limit'))
    this.buffer = this.buffer.length === 0 ? bytes : Buffer.concat([this.buffer, bytes])
    while (true) {
      let text
      if (this.lineMode) {
        const newline = this.buffer.indexOf(0x0a)
        if (newline < 0) return
        // Decode the whole frame at once; headers and JSON are ASCII-framed, so
        // the byte offset of `\n` is exact.
        text = this.buffer.subarray(0, newline).toString('utf8').trim()
        this.buffer = this.buffer.subarray(newline + 1)
        if (!text) continue
      } else {
        const separator = this.buffer.indexOf('\r\n\r\n')
        const alternate = separator >= 0 ? -1 : this.buffer.indexOf('\n\n')
        const headerEnd = separator >= 0 ? separator : alternate
        if (headerEnd < 0) return
        const terminator = separator >= 0 ? 4 : 2
        const header = this.buffer.subarray(0, headerEnd).toString('latin1')
        const match = header.match(/(?:^|\r?\n)content-length:\s*(\d+)\s*$/im)
        if (!match) return this.#fail(providerError('MCP process returned malformed headers', 'malformed_result'))
        const bodyStart = headerEnd + terminator
        const length = Number(match[1])
        if (this.buffer.length - bodyStart < length) return
        text = this.buffer.subarray(bodyStart, bodyStart + length).toString('utf8')
        this.buffer = this.buffer.subarray(bodyStart + length)
      }
      let message
      try { message = JSON.parse(text) } catch { return this.#fail(providerError('MCP process returned malformed JSON', 'malformed_result')) }
      if (message.id === undefined) continue
      const pending = this.pending.get(message.id)
      if (!pending) continue
      this.pending.delete(message.id)
      pending.resolve(message)
    }
  }

  #fail(error) {
    if (this.closed) return
    this.closed = true
    for (const pending of this.pending.values()) pending.reject(error)
    this.pending.clear()
  }

  call(id, method, params) {
    if (this.closed) return Promise.reject(providerError('MCP process is closed', 'process_error'))
    const message = { jsonrpc: '2.0', id, method, ...(params === undefined ? {} : { params }) }
    return withAbort(this.signal, new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject })
      try { this.write(message) } catch { this.pending.delete(id); reject(providerError('MCP process write failed', 'process_error')) }
    }))
  }

  notify(method, params) {
    if (this.closed) throw providerError('MCP process is closed', 'process_error')
    this.write({ jsonrpc: '2.0', method, ...(params === undefined ? {} : { params }) })
  }

  write(message) {
    const text = JSON.stringify(message)
    if (this.lineMode) this.child.stdin.write(`${text}\n`)
    else this.child.stdin.write(`Content-Length: ${Buffer.byteLength(text)}\r\n\r\n${text}`)
  }

  close() {
    if (this.closed) return
    this.#fail(providerError('MCP process closed', 'process_error'))
    this.signal?.removeEventListener('abort', this.onAbort)
  }
}

export class PythonSearchBridge {
  constructor(options = {}) {
    this.spawn = options.spawn ?? defaultSpawn
    this.command = options.command
    this.args = options.args
    this.baseEnv = options.env ?? process.env
    this.maxOutputBytes = options.maxOutputBytes ?? MAX_OUTPUT_BYTES
    this.lineMode = options.lineMode !== false
  }

  async search({ query, maxResults, providers, entries, resolveValue, timeoutMs, signal, timeRange, grokMode }) {
    if (!Array.isArray(providers) || providers.length === 0) {
      throw providerError('No Python search providers are configured', 'configuration')
    }
    const childSignal = signal
    if (childSignal?.aborted) throw childSignal.reason ?? abortError()
    const environment = await buildEnvironment({
      baseEnv: this.baseEnv,
      entries,
      providers,
      resolveValue,
      signal: childSignal,
      timeoutMs,
    })
    const command = readEnvironment({ command: this.command, args: this.args, environment: this.baseEnv })
    let child
    try {
      child = this.spawn(command.command, command.args, { env: environment, stdio: ['pipe', 'pipe', 'pipe'] })
      if (childSignal?.aborted) throw childSignal.reason ?? abortError()
      const timeout = timeoutMs > 0 ? AbortSignal.timeout(timeoutMs) : undefined
      const combined = timeout && childSignal ? AbortSignal.any([childSignal, timeout]) : (timeout ?? childSignal)
      const request = new StdioRpc(child, combined, this.maxOutputBytes, this.lineMode)
      const initialized = await request.call(1, 'initialize', {
        protocolVersion: DEFAULT_PROTOCOL_VERSION,
        capabilities: {},
        clientInfo: { name: PACKAGE_NAME, version: PACKAGE_VERSION },
      })
      if (initialized.error) throw providerError('MCP initialization failed', 'protocol_error')
      request.notify('notifications/initialized')
      const envelope = await request.call(2, 'tools/call', {
        name: 'web_search',
        arguments: {
          query, providers,
          // Omitted stays omitted: the core default (5) applies. Sending a
          // DSH-side substitute here would silently override the core contract.
          ...(maxResults !== undefined ? { max_results: maxResults } : {}),
          ...(timeRange ? { time_range: timeRange } : {}),
          // Python rejects grok_search_mode unless grok is enabled, and each
          // attempt requests exactly one provider, so gate on the kind.
          ...(grokMode && providers.includes('grok') ? { grok_search_mode: grokMode } : {}),
        },
      })
      return mapProviderPayload(parseToolEnvelope(envelope), providers[0])
    } catch (error) {
      if (childSignal?.aborted) throw childSignal.reason ?? abortError()
      if (error?.name === 'TimeoutError') throw timeoutError()
      if (error?.name === 'AbortError') throw error
      throw error?.code ? error : providerError('Python search bridge failed', 'bridge_error')
    } finally {
      if (child) {
        try { child.stdin?.end() } catch {}
        try { child.kill('SIGTERM') } catch {}
      }
    }
  }
}

async function buildEnvironment({ baseEnv, entries, providers, resolveValue, signal, timeoutMs }) {
  const env = { ...baseEnv }
  env.AGENT_WEB_SEARCH_PROVIDERS = providers.join(',')
  env.AGENT_WEB_SEARCH_TIMEOUT = String(Math.max(0.001, timeoutMs / 1000))
  env.AGENT_WEB_SEARCH_MCP_TRANSPORT = 'stdio'
  for (const [name, variable] of Object.entries(CREDENTIAL_ENV)) delete env[variable]
  for (const variable of Object.values(ENDPOINT_ENV)) delete env[variable]
  for (const variable of Object.values(MODEL_ENV)) delete env[variable]
  for (const variable of Object.values(TOOL_TYPE_ENV)) delete env[variable]
  for (const variable of Object.values(TOOL_NAME_ENV)) delete env[variable]
  for (const variable of Object.values(BASE_URL_ENV)) delete env[variable]
  for (const variable of EXTRA_ENDPOINT_ENV) delete env[variable]
  for (const entry of entries ?? []) {
    if (!providers.includes(entry.kind)) continue
    const modelEnv = MODEL_ENV[entry.kind]
    if (modelEnv && typeof entry.models === 'string' && entry.models.trim()) {
      env[modelEnv] = entry.models.trim()
    }
    const toolTypeEnv = TOOL_TYPE_ENV[entry.kind]
    if (toolTypeEnv && typeof entry.toolType === 'string' && entry.toolType.trim()) {
      env[toolTypeEnv] = entry.toolType.trim()
    }
    const toolNameEnv = TOOL_NAME_ENV[entry.kind]
    if (toolNameEnv && typeof entry.toolName === 'string' && entry.toolName.trim()) {
      env[toolNameEnv] = entry.toolName.trim()
    }
    const credentialEnv = CREDENTIAL_ENV[entry.kind]
    if (credentialEnv && entry.credentialRef && typeof resolveValue === 'function') {
      const value = await withAbort(signal, Promise.resolve(resolveValue(entry.credentialRef, signal)))
      if (typeof value === 'string' && value.trim()) env[credentialEnv] = value
    }
    // Only kinds whose Python provider actually reads an endpoint variable get
    // one; for the rest this would write an environment variable nothing reads.
    if (entry.baseURL && ENDPOINT_OVERRIDE_KINDS.includes(entry.kind)) {
      const endpoint = endpointValue(entry.baseURL)
      const variable = BASE_URL_ENV[entry.kind] ?? ENDPOINT_ENV[entry.kind]
      if (variable) env[variable] = endpoint
      if (entry.kind === 'exa') {
        env.EXA_MCP_URL = endpoint
        env.AGENT_WEB_SEARCH_EXA_ENDPOINT = endpoint
      }
      if (entry.kind === 'parallel') {
        env.AGENT_WEB_SEARCH_PARALLEL_MCP_URL = endpoint
        env.AGENT_WEB_SEARCH_PARALLEL_ENDPOINT = endpoint
      }
    }
  }
  return env
}

function normalizedKey(url) {
  try {
    const parsed = new URL(url)
    parsed.hash = ''
    return parsed.href.replace(/\/$/, '').toLowerCase()
  } catch { return url }
}

// Dedupe-only merge. The bridge no longer caps the merged list: `max_results`
// bounds what each upstream is asked for, and the core already applies it, so
// every returned row is passed through (after optional URL dedupe).
function mergeOutcomes(outcomes, dedupeByUrl) {
  const sources = []
  const seen = new Set()
  const answers = []
  for (const outcome of outcomes) {
    if (outcome?.content) answers.push(outcome.content)
    for (const source of outcome?.sources ?? []) {
      const key = normalizedKey(source.url)
      if (dedupeByUrl && seen.has(key)) continue
      seen.add(key)
      sources.push(source)
    }
  }
  return {
    sources,
    // Nothing is dropped here anymore, so this stays false unless an upstream
    // outcome reported its own truncation.
    truncated: outcomes.some(outcome => outcome?.truncated === true),
    ...(answers.length > 0 ? { content: answers.join('\n\n---\n\n') } : {}),
  }
}

export function mergeBridgeOutcomes(outcomes, dedupeByUrl = true) {
  return mergeOutcomes(outcomes, dedupeByUrl)
}

export { mapProviderPayload, parseToolEnvelope }
