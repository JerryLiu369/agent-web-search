// Process-local, bounded diagnostics. Never retain queries, credentials, URLs,
// snippets, responses, or upstream error messages in the browser-readable view.
import { PROVIDER_KINDS } from './defaults.js'

const LIMIT = 50
// Keep the allowlist tied to the adapter registry's supported kinds so a new
// source cannot silently disappear from diagnostics while still being queried.
const KINDS = new Set(PROVIDER_KINDS)
const STATUSES = new Set(['success', 'empty', 'failed', 'timeout', 'cancelled'])
const integer = value => Number.isFinite(value) ? Math.max(0, Math.floor(value)) : 0

export class SearchHistory {
  #entries = []
  #nextId = 1

  record(event) {
    const attempts = Array.isArray(event.attempts) ? event.attempts : []
    const entry = {
      id: this.#nextId++,
      at: new Date().toISOString(),
      provider: 'agent-web-search',
      mode: event.mode === 'fallback' ? 'fallback' : 'fanout',
      status: event.status === 'success' ? 'success' : event.status === 'aborted' ? 'aborted' : 'failed',
      durationMs: integer(event.durationMs),
      resultCount: integer(event.resultCount),
      attempts: attempts.slice(0, 60).filter(item => KINDS.has(item.kind)).map(item => ({
        kind: item.kind,
        status: STATUSES.has(item.status) ? item.status : 'failed',
        durationMs: integer(item.durationMs),
        resultCount: integer(item.resultCount),
        ...(Number.isInteger(item.httpStatus) && item.httpStatus >= 100 && item.httpStatus <= 599
          ? { httpStatus: item.httpStatus } : {}),
      })),
    }
    this.#entries.unshift(entry)
    if (this.#entries.length > LIMIT) this.#entries.length = LIMIT
  }

  snapshot() {
    return { entries: this.#entries.map(entry => ({
      ...entry,
      attempts: entry.attempts.map(attempt => ({ ...attempt })),
    })) }
  }
}
