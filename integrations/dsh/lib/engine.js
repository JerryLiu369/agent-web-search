import { isSafeSourceUrl, mergeBridgeOutcomes } from './bridge.js'
import { KIND_LABEL } from './defaults.js'

function timeoutSignal(parent, milliseconds) {
  const timeout = AbortSignal.timeout(milliseconds)
  return parent ? AbortSignal.any([parent, timeout]) : timeout
}

function isCallerAbort(error, signal) {
  return signal?.aborted === true || (error?.name === 'AbortError' && signal?.aborted === true)
}

function reasonFor(error) {
  if (error?.code === 'timeout' || error?.name === 'TimeoutError') return 'timeout'
  if (error?.code === 'all_providers_failed') return 'all providers failed'
  if (error?.code === 'malformed_result') return 'malformed MCP result'
  if (error?.code === 'output_limit') return 'output limit exceeded'
  return 'failed'
}

async function runOne({ entry, query, maxResults, attemptTimeoutMs, signal, resolveValue, bridge, timeRange, grokMode }) {
  const startedAt = Date.now()
  const attemptSignal = timeoutSignal(signal, attemptTimeoutMs)
  try {
    const result = await bridge.search({
      query, maxResults, providers: [entry.kind], entries: [entry], resolveValue,
      timeoutMs: attemptTimeoutMs, signal: attemptSignal, timeRange, grokMode,
    })
    return { result, elapsedMs: Date.now() - startedAt }
  } catch (error) {
    if (isCallerAbort(error, signal)) throw error
    const wrapped = error instanceof Error ? error : new Error('provider unavailable')
    wrapped.elapsedMs = Date.now() - startedAt
    throw wrapped
  }
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function sourceFromCore(entry, row) {
  const label = KIND_LABEL[entry.kind] ?? entry.kind
  return {
    title: `【来源：${label}】${row.title.length > 0 ? ` ${row.title}` : ''}`,
    url: row.url,
    ...(row.description.length > 0 ? { snippet: row.description } : {}),
    ...(row.published_at !== undefined ? { publishedAt: row.published_at } : {}),
    ...(row.author !== undefined ? { author: row.author } : {}),
  }
}

function failureDetails(item) {
  if (!item.providerErrors || typeof item.providerErrors !== 'object' || Array.isArray(item.providerErrors)) {
    return item.reason
  }
  return Object.prototype.hasOwnProperty.call(item.providerErrors, item.kind)
    ? item.providerErrors[item.kind]
    : item.providerErrors
}

function normalizeOutcome(entry, result, includeAnswer) {
  // The bridge validates the child's payload, so the expected provider is always
  // present here; anything else is treated as an empty response rather than
  // reintroducing a second legacy normalization path.
  const rawProvider = isObject(result?.providers) && isObject(result.providers[entry.kind])
    ? result.providers[entry.kind]
    : { results: [] }
  const rows = Array.isArray(rawProvider.results) ? rawProvider.results : []
  const results = rows.filter(row => isSafeSourceUrl(row?.url)).map(row => ({
    title: row.title,
    url: row.url,
    description: row.description,
    ...(row.published_at !== undefined ? { published_at: row.published_at } : {}),
    ...(row.author !== undefined ? { author: row.author } : {}),
  }))
  const provider = {
    // `answer` is part of the core model-facing payload. The DSH setting only
    // controls whether the separate citation-card projection includes it.
    ...(typeof rawProvider.answer === 'string' ? { answer: rawProvider.answer } : {}),
    results,
  }
  return {
    query: typeof result?.query === 'string' ? result.query : undefined,
    providers: { [entry.kind]: provider },
    sources: results.map(row => sourceFromCore(entry, row)),
    ...(includeAnswer && provider.answer !== undefined ? { content: provider.answer } : {}),
  }
}

export async function runSearch({
  mode, providers, query, maxResults, attemptTimeoutMs, totalTimeoutMs, dedupeByUrl,
  includeAnswer, timeRange, grokMode, signal, resolveValue, bridge, onAttempt, logger,
}) {
  const totalSignal = timeoutSignal(signal, totalTimeoutMs)
  const outcomes = []
  const failures = []

  const observeFailure = (entry, error) => {
    const event = {
      kind: entry.kind,
      status: reasonFor(error),
      durationMs: error?.elapsedMs ?? 0, resultCount: 0,
      ...(error?.status ? { httpStatus: error.status } : {}),
    }
    failures.push({ kind: entry.kind, reason: event.status, providerErrors: error?.providerErrors })
    onAttempt?.(event)
    logger?.warn?.('agent-web-search: %s failed: %s', event.kind, event.status)
  }

  const observeSuccess = (entry, outcome, elapsedMs) => {
    const result = normalizeOutcome(entry, outcome, includeAnswer)
    outcomes.push({ kind: entry.kind, ...result })
    const status = result.sources.length > 0 || (includeAnswer && result.content) ? 'success' : 'empty'
    onAttempt?.({
      kind: entry.kind,
      status,
      durationMs: elapsedMs,
      resultCount: result.sources.length,
    })
    logger?.info?.('agent-web-search: %s served the query in %d ms (%d rows)', entry.kind, elapsedMs, result.sources.length)
    // An empty but valid provider response is still a successful provider in
    // the core contract and must remain under `providers`.
    return true
  }

  const runEntry = async entry => {
    try {
      const { result, elapsedMs } = await runOne({
        entry, query, maxResults, attemptTimeoutMs, signal: totalSignal, resolveValue, bridge, timeRange, grokMode,
      })
      return observeSuccess(entry, result, elapsedMs)
    } catch (error) {
      if (signal?.aborted) throw signal.reason ?? error
      if (totalSignal.aborted && !signal?.aborted) throw timeoutSignalError()
      observeFailure(entry, error)
      return false
    }
  }

  if (mode === 'fallback') {
    for (const entry of providers) {
      if (totalSignal.aborted) throw timeoutSignalError()
      if (await runEntry(entry)) break
    }
  } else {
    const jobs = providers.map(entry => runEntry(entry))
    await Promise.all(jobs)
  }

  if (signal?.aborted) throw signal.reason ?? new DOMException('search aborted', 'AbortError')
  if (totalSignal.aborted) throw timeoutSignalError()
  if (outcomes.length === 0) {
    const error = new Error('All configured search providers failed')
    error.code = 'all_providers_failed'
    error.providerErrors = Object.fromEntries(failures.map(item => [
      item.kind,
      failureDetails(item),
    ]))
    throw error
  }
  const merged = mergeBridgeOutcomes(outcomes, dedupeByUrl)
  const byKind = new Map(outcomes.map(item => [item.kind, item]))
  const publicProviders = {}
  for (const entry of providers) {
    const outcome = byKind.get(entry.kind)
    if (outcome) publicProviders[entry.kind] = outcome.providers[entry.kind]
  }
  const first = outcomes[0]
  return {
    query: first.query ?? query,
    providers: publicProviders,
    ...merged,
    failures,
  }
}

function timeoutSignalError() {
  const error = new Error('search timed out')
  error.name = 'TimeoutError'
  error.code = 'timeout'
  return error
}
