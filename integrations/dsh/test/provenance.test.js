import test from 'node:test'
import assert from 'node:assert/strict'
import { mergeBridgeOutcomes, mapProviderPayload, parseToolEnvelope } from '../lib/bridge.js'

test('native provider payload preserves the exact core fields, answers, and result provenance', () => {
  const result = mapProviderPayload({
    query: 'question',
    providers: {
      ddgs: {
        answer: 'A readable answer',
        results: [{
          title: '  Exact title  ',
          url: 'HTTPS://Example.org/path/?q=1',
          description: 'Summary',
          published_at: '2025-01-02T03:04:05Z',
          author: 'Author',
          ignored: 'not part of the core schema',
        }],
      },
    },
  }, 'ddgs')
  assert.deepEqual(result, {
    query: 'question',
    providers: {
      ddgs: {
        answer: 'A readable answer',
        results: [{
          title: '  Exact title  ',
          url: 'HTTPS://Example.org/path/?q=1',
          description: 'Summary',
          published_at: '2025-01-02T03:04:05Z',
          author: 'Author',
        }],
      },
    },
  })
})

test('empty answers are accepted but omitted, and empty results are valid', () => {
  assert.deepEqual(mapProviderPayload({
    query: 'no hits',
    providers: {
      ddgs: { answer: '', results: [] },
      exa: { results: [] },
    },
  }), {
    query: 'no hits',
    providers: {
      ddgs: { results: [] },
      exa: { results: [] },
    },
  })
})

test('every returned row is preserved; the bridge never truncates', () => {
  const result = mapProviderPayload({
    query: 'q',
    providers: {
      ddgs: { results: [
        { title: 'D1', url: 'https://example.org/d1', description: 'D1' },
        { title: 'D2', url: 'https://example.org/d2', description: 'D2' },
        { title: 'D3', url: 'https://example.org/d3', description: 'D3' },
      ] },
      exa: { results: [
        { title: 'E1', url: 'https://example.org/e1', description: 'E1' },
        { title: 'E2', url: 'https://example.org/e2', description: 'E2' },
        { title: 'E3', url: 'https://example.org/e3', description: 'E3' },
      ] },
    },
  })
  // `max_results` is a per-call request input the core already applied; DSH
  // passes every row through instead of shortening the payload.
  assert.deepEqual(result.providers.ddgs.results.map(row => row.title), ['D1', 'D2', 'D3'])
  assert.deepEqual(result.providers.exa.results.map(row => row.title), ['E1', 'E2', 'E3'])
})

test('missing and malformed core or result fields are rejected', () => {
  const invalidPayloads = [
    { providers: {} },
    { query: 'q' },
    { query: 42, providers: {} },
    { query: 'q', providers: { ddgs: {} } },
    { query: 'q', providers: { ddgs: { results: [{}] } } },
    { query: 'q', providers: { ddgs: { results: [{ title: 'T', url: 'https://example.org/a' }] } } },
    { query: 'q', providers: { ddgs: { results: [{ title: 'T', url: 42, description: 'D' }] } } },
    { query: 'q', providers: { ddgs: { results: [{ title: 'T', url: 'https://example.org/a', description: 'D', published_at: 42 }] } } },
    { query: 'q', providers: { ddgs: { results: [{ title: 'T', url: 'https://example.org/a', description: 'D', author: 42 }] } } },
    { query: 'q', providers: { ddgs: { answer: 42, results: [] } } },
  ]
  for (const payload of invalidPayloads) {
    assert.throws(() => mapProviderPayload(payload), error => error.code === 'malformed_result')
  }
})

test('unsafe URLs are dropped per row without failing the provider', () => {
  const result = mapProviderPayload({
    query: 'q',
    providers: {
      ddgs: {
        answer: 'kept',
        results: [
          { title: 'safe', url: 'https://example.org/ok', description: 'kept' },
          { title: 'script', url: 'javascript:alert(1)', description: 'dropped' },
          { title: 'data', url: 'data:text/plain,hi', description: 'dropped' },
          { title: 'credentialed', url: 'https://user:pass@example.org/', description: 'dropped' },
          { title: 'fragment', url: 'https://example.org/page#fragment', description: 'dropped' },
          { title: 'also safe', url: 'http://127.0.0.1:8080/x', description: 'kept' },
        ],
      },
    },
  }, 'ddgs')
  // One bad row must never take down the whole provider: the safe rows and the
  // provider answer survive, so a compromised upstream gains no DoS lever.
  assert.deepEqual(result.providers.ddgs.results.map(row => row.title), ['safe', 'also safe'])
  assert.equal(result.providers.ddgs.answer, 'kept')
})

test('a provider whose every row is unsafe still succeeds as an empty result', () => {
  const result = mapProviderPayload({
    query: 'q',
    providers: { ddgs: { results: [{ title: 'x', url: 'javascript:alert(1)', description: 'y' }] } },
  }, 'ddgs')
  assert.deepEqual(result.providers.ddgs.results, [])
})

test('unexpected provider payload is rejected', () => {
  assert.throws(() => mapProviderPayload({
    query: 'q',
    providers: { exa: { results: [] } },
  }, 'ddgs'), error => error.code === 'malformed_result')
})

test('bridge aggregation deduplicates by URL without truncating', () => {
  const result = mergeBridgeOutcomes([
    { sources: [{ title: 'A', url: 'https://example.org/a', provider: 'ddgs' }] },
    { sources: [{ title: 'duplicate', url: 'https://example.org/a/', provider: 'exa' }, { title: 'B', url: 'https://example.org/b', provider: 'exa' }] },
  ], true)
  assert.deepEqual(result.sources.map(source => source.url), ['https://example.org/a', 'https://example.org/b'])
  assert.equal(result.sources.length, 2)
  assert.equal(result.truncated, false)
})

test('bridge aggregation keeps every distinct row past any former cap', () => {
  const many = Array.from({ length: 30 }, (_, index) => ({
    title: `T${index}`, url: `https://example.org/${index}`, provider: 'ddgs',
  }))
  const result = mergeBridgeOutcomes([{ sources: many }], true)
  assert.equal(result.sources.length, 30)
  assert.equal(result.truncated, false)
})

test('malformed and provider-error MCP results are sanitized', () => {
  assert.throws(() => parseToolEnvelope({ result: { content: [{ type: 'text', text: 'not-json' }] } }), error => error.code === 'malformed_result')
  assert.throws(() => parseToolEnvelope({ result: { isError: true, content: [{ type: 'text', text: JSON.stringify({ error: { code: 'all_providers_failed', provider_errors: { ddgs: 'ddgs RuntimeError' } } }) }] } }), error => {
    assert.equal(error.code, 'all_providers_failed')
    assert.deepEqual(error.providerErrors, { ddgs: 'ddgs RuntimeError' })
    return true
  })
})

test('provider answers remain available to the native payload', () => {
  const result = mapProviderPayload({
    query: 'q',
    providers: { codex_alpha: { answer: 'Alpha says hi', results: [] } },
  }, 'codex_alpha')
  assert.equal(result.providers.codex_alpha.answer, 'Alpha says hi')
})
