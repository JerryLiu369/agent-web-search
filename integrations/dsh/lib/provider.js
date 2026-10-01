import { WebError } from '@deepseek-ai/dsh-web'
import { KIND_CREDENTIAL_REF, PROVIDER_KINDS, AGENT_WEB_SEARCH_PROVIDER_ID } from './defaults.js'
import { resolveConfig, snapshotsOf } from './config.js'
import { PythonSearchBridge } from './bridge.js'
import { runSearch } from './engine.js'

/**
 * Message on the `WebError` thrown when every enabled upstream failed.
 *
 * Exported because the native tool has to recognise this failure after DSH has
 * re-thrown the error, where only the message may survive: importing it keeps
 * the two copies from drifting apart.
 */
export const ALL_SOURCES_FAILED_MESSAGE = 'agent-web-search: all configured sources failed'

export class AgentWebSearchProvider {
  id = AGENT_WEB_SEARCH_PROVIDER_ID

  constructor(options = {}) {
    this.options = options
    this.bridge = options.bridge ?? new PythonSearchBridge(options.bridgeOptions)
  }

  /**
   * Read the live config without letting a raw schema `ValidationError` escape.
   *
   * `available()` is documented by the web seam as a cheap usability check that
   * runs on every resolution, so it must answer `false` rather than throw; and a
   * nested schema path in an exception message must never reach the model.
   *
   * @returns {{config: object} | {error: unknown}} the resolved config or the failure.
   */
  #resolvedConfig() {
    try {
      return { config: resolveConfig(snapshotsOf(this.options.config())) }
    } catch (error) {
      return { error }
    }
  }

  available() {
    const { config } = this.#resolvedConfig()
    if (!config) return false
    return config.providers.some(entry => entry.enabled !== false && PROVIDER_KINDS.includes(entry.kind))
  }

  async search(request, signal, overrides = {}) {
    const { config } = this.#resolvedConfig()
    if (!config) {
      throw new WebError('agent-web-search: the plugin configuration is invalid', 'WEB_PROVIDER_UNAVAILABLE')
    }
    let entries = config.providers
      .filter(entry => entry.enabled !== false && PROVIDER_KINDS.includes(entry.kind))
      .map(entry => ({
        ...entry,
        credentialRef: KIND_CREDENTIAL_REF[entry.kind],
      }))
    // Per-call provider subset for the model-facing tool: the caller validated
    // names already, so an empty intersection simply means no enabled sources.
    if (Array.isArray(overrides.providers) && overrides.providers.length > 0) {
      const wanted = new Set(overrides.providers)
      const order = new Map(overrides.providers.map((kind, index) => [kind, index]))
      entries = entries
        .filter(entry => wanted.has(entry.kind))
        .sort((a, b) => order.get(a.kind) - order.get(b.kind))
    }
    const startedAt = Date.now()
    const attempts = []
    const finish = (status, resultCount = 0) => {
      try {
        this.options.record?.({
          mode: config.mode,
          status,
          resultCount,
          durationMs: Date.now() - startedAt,
          attempts,
        })
      } catch {}
    }
    if (entries.length === 0) {
      finish('failed')
      throw new WebError('agent-web-search has no enabled sources', 'WEB_PROVIDER_UNAVAILABLE')
    }
    // `max_results` is a per-call request input, never persistent configuration
    // (ARCHITECTURE.md: request inputs are not configuration). Omitted means
    // the core default (5) applies downstream; DSH must not substitute its own.
    const maxResults = Number.isFinite(request?.maxResults) && request.maxResults > 0
      ? Math.min(20, Math.floor(request.maxResults))
      : undefined
    const resolveValue = async (ref, childSignal) => {
      if (!ref || typeof this.options.resolveValue !== 'function') return undefined
      const promise = this.options.resolveValue(ref)
      if (!childSignal) return promise
      return Promise.race([
        promise,
        new Promise((_, reject) => childSignal.addEventListener('abort', () => reject(childSignal.reason), { once: true })),
      ])
    }
    try {
      const outcome = await runSearch({
        mode: config.mode,
        providers: entries,
        query: request?.query,
        // Per-call only: no card defaults. Omitted means Python defaults.
        timeRange: overrides.timeRange,
        grokMode: overrides.grokMode,
        maxResults,
        attemptTimeoutMs: config.attemptTimeoutMs,
        totalTimeoutMs: config.totalTimeoutMs,
        dedupeByUrl: config.dedupeByUrl,
        includeAnswer: config.includeAnswer,
        signal,
        resolveValue,
        bridge: this.bridge,
        onAttempt: event => attempts.push(event),
        logger: this.options.logger,
      })
      finish('success', outcome.sources.length)
      return {
        query: outcome.query,
        providers: outcome.providers,
        // These fields are an internal DSH citation projection. The native
        // model tool returns only query/providers so it stays MCP-compatible.
        sources: outcome.sources,
        truncated: outcome.truncated,
        ...(outcome.content !== undefined ? { content: outcome.content } : {}),
      }
    } catch (error) {
      if (signal?.aborted || error?.name === 'AbortError') {
        finish('aborted')
        throw new WebError('agent-web-search: search aborted', 'WEB_ABORTED')
      }
      if (error?.name === 'TimeoutError' || error?.code === 'timeout') {
        finish('timeout')
        throw new WebError('agent-web-search: search timed out', 'WEB_PROVIDER_ERROR')
      }
      finish('failed')
      const wrapped = new WebError(ALL_SOURCES_FAILED_MESSAGE, 'WEB_PROVIDER_ERROR')
      if (error?.code === 'all_providers_failed') {
        wrapped.searchCode = 'all_providers_failed'
        wrapped.providerErrors = error.providerErrors
      }
      throw wrapped
    }
  }
}
