import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { parseToolArgs, registerWebSearchTool } from '../lib/tool.js'
import { AgentWebSearchProvider } from '../lib/provider.js'

const BASE_PROVIDERS = [
  { kind: 'ddgs', enabled: true, baseURL: '' },
  { kind: 'exa', enabled: true, baseURL: '' },
  { kind: 'grok', enabled: false, baseURL: '' },
]

function config(overrides = {}) {
  const wrap = value => ({ get: () => value })
  return {
    mode: wrap('fanout'), providers: wrap(BASE_PROVIDERS),
    attemptTimeoutMs: wrap(2000), totalTimeoutMs: wrap(5000),
    dedupeByUrl: wrap(true), includeAnswer: wrap(false),
    ...overrides,
  }
}

const okPayload = ({ query, providers }) => ({
  query,
  providers: {
    [providers[0]]: { results: [{ title: 'A', url: 'https://example.org/a', description: 'summary' }] },
  },
})

function fakeBridge(impl = okPayload) {
  const calls = []
  return {
    calls,
    bridge: { async search(args) { calls.push(args); return impl(args) } },
  }
}

function setup({ existingTool, cfg, impl } = {}) {
  const stages = { tool: undefined, sections: [] }
  const { calls, bridge } = fakeBridge(impl)
  const ctx = {
    tools: {
      get: name => (name === 'web_search' ? existingTool : undefined),
      register: definition => { stages.tool = definition; return () => {} },
    },
    systemPrompt: {
      section: definition => stages.sections.push(definition),
      getSectionOrder: () => 0,
    },
    logger: { warn: () => {}, info: () => {} },
  }
  const provider = new AgentWebSearchProvider({
    config: () => cfg ?? config(),
    resolveValue: async () => undefined,
    record: () => {},
    bridge,
  })
  registerWebSearchTool(ctx, { config: () => cfg ?? config(), provider })
  return { stages, calls }
}

test('registers web_search with the MCP-consistent schema', () => {
  const { stages } = setup()
  assert.equal(stages.tool.name, 'web_search')
  const params = stages.tool.parameters
  const props = params.properties
  // grok is disabled here, so grok_search_mode stays out of the schema,
  // exactly like the Python operation builds it.
  assert.deepEqual(Object.keys(props).sort(), ['max_results', 'providers', 'query', 'time_range'])
  assert.deepEqual(params.required, ['query'])
  assert.deepEqual(props.time_range.enum, ['d', 'w', 'm', 'y'])
  assert.deepEqual(props.providers.items.enum, ['ddgs', 'exa'])
  assert.equal(stages.sections.map(section => section.name).includes('tool:web_search'), true)
})

test('schema gains grok_search_mode only when grok is enabled', () => {
  const wrap = value => ({ get: () => value })
  const grokOn = config({
    providers: wrap([
      { kind: 'ddgs', enabled: true, baseURL: '' },
      { kind: 'grok', enabled: true, baseURL: '' },
    ]),
  })
  const { stages } = setup({ cfg: grokOn })
  const props = stages.tool.parameters.properties
  assert.deepEqual(props.grok_search_mode.enum, ['web_search', 'x_search', 'both'])
  assert.deepEqual(props.providers.items.enum, ['ddgs', 'grok'])
})

test('skips registration when a web_search tool already exists', () => {
  const { stages } = setup({ existingTool: { name: 'web_search' } })
  assert.equal(stages.tool, undefined)
})

test('executes with per-call args and returns the core provider envelope', async () => {
  const { stages, calls } = setup()
  const result = await stages.tool.execute(
    { query: 'latest news', max_results: 3, time_range: 'w' },
    { signal: undefined },
  )
  assert.equal(calls.length, 2)
  assert.deepEqual(calls.map(call => call.providers), [['ddgs'], ['exa']])
  assert.ok(calls.every(call => call.timeRange === 'w'))
  assert.ok(calls.every(call => call.maxResults === 3))
  assert.equal(result.query, 'latest news')
  assert.deepEqual(Object.keys(result.providers), ['ddgs', 'exa'])
  assert.equal(result.providers.ddgs.results[0].url, 'https://example.org/a')
  assert.equal(result.providers.exa.results[0].description, 'summary')
})

test('omitted max_results stays omitted so the core default applies', async () => {
  const { stages, calls } = setup()
  await stages.tool.execute({ query: 'q', providers: ['ddgs'] }, { signal: undefined })
  assert.equal(calls.length, 1)
  // No DSH-side substitute: `max_results` is a per-call request input, so the
  // core default (10) still applies downstream.
  assert.equal(calls[0].maxResults, undefined)
})

test('keeps provider answers in the model payload when card answers are disabled', async () => {
  const { stages } = setup({
    impl: ({ query, providers }) => ({
      query,
      providers: { [providers[0]]: { answer: 'core answer', results: [] } },
    }),
  })
  const result = await stages.tool.execute({ query: 'q', providers: ['ddgs'] }, { signal: undefined })
  assert.deepEqual(result, {
    query: 'q',
    providers: { ddgs: { answer: 'core answer', results: [] } },
  })
})

test('returns the canonical structured all-provider failure envelope', async () => {
  const { stages } = setup({
    impl: ({ providers }) => {
      const error = new Error('upstream details must stay internal')
      error.code = 'all_providers_failed'
      error.providerErrors = { [providers[0]]: 'provider unavailable' }
      throw error
    },
  })
  const result = await stages.tool.execute({ query: 'q', providers: ['ddgs'] }, { signal: undefined })
  assert.deepEqual(result, {
    error: {
      code: 'all_providers_failed',
      message: 'All enabled search providers failed. Check provider configuration, credentials, quotas, and network access.',
      provider_errors: { ddgs: 'provider unavailable' },
    },
    query: 'q',
  })
})

test('honors provider subsets and falls back to card defaults', async () => {
  const { stages, calls } = setup()
  await stages.tool.execute({ query: 'q', providers: ['exa'] }, { signal: undefined })
  assert.deepEqual(calls.map(call => call.providers), [['exa']])
  assert.equal(calls[0].timeRange, undefined)
  assert.equal(calls[0].grokMode, undefined)
})

test('rejects MCP-inconsistent arguments like the Python operation', async () => {
  const { stages } = setup()
  await assert.rejects(stages.tool.execute({ query: 'q', max_results: 99 }, {}), /max_results must be an integer between 1 and 20/)
  await assert.rejects(stages.tool.execute({ query: 'q', time_range: 'x' }, {}), /time_range/)
  await assert.rejects(stages.tool.execute({ query: 'q', providers: ['nope'] }, {}), /providers/)
  await assert.rejects(stages.tool.execute({ query: 'q', grok_search_mode: 'both' }, {}), /grok_search_mode is only available when grok is enabled/)
  await assert.rejects(stages.tool.execute({ query: '  ' }, {}), /query must be a non-empty string/)
})

test('passes grok_search_mode through on grok attempts', async () => {
  const wrap = value => ({ get: () => value })
  const cfg = config({ providers: wrap([{ kind: 'grok', enabled: true, baseURL: '' }]) })
  const { stages, calls } = setup({ cfg })
  await stages.tool.execute({ query: 'q', grok_search_mode: 'x_search' }, { signal: undefined })
  assert.equal(calls.length, 1)
  assert.equal(calls[0].grokMode, 'x_search')
})

test('parseToolArgs mirrors the same contract without a registry', () => {
  assert.deepEqual(parseToolArgs({ query: 'q' }, ['ddgs']), { query: 'q' })
  assert.deepEqual(
    parseToolArgs({ query: 'q', max_results: 2, time_range: 'd', providers: ['exa'], grok_search_mode: 'web_search' }, ['exa', 'grok']),
    { query: 'q', maxResults: 2, timeRange: 'd', providers: ['exa'], grokMode: 'web_search' },
  )
})

test('presenters title cards by query and carry structured sources', () => {
  const { stages } = setup()
  const call = stages.tool.presentCall({ query: 'hello' })
  assert.equal(call.title, 'hello')
  assert.equal(call.kind, 'search')
  const shown = stages.tool.presentResult({ query: 'hello' }, {
    isError: false,
    meta: { sources: [{ url: 'https://example.org/a' }], truncated: false },
  })
  assert.equal(shown.card, 'web')
  assert.deepEqual(shown.sources, [{ url: 'https://example.org/a' }])
})

test('the citation card shows every distinct row and reports no truncation', () => {
  const { stages } = setup()
  const rows = Array.from({ length: 25 }, (_, index) => ({
    title: `T${index}`,
    url: `https://example.org/${index}`,
    description: `D${index}`,
  }))
  // Even a per-call max_results must not shorten what the card displays.
  const meta = stages.tool.output.presentationMeta(
    { query: 'q', max_results: 3 },
    { query: 'q', providers: { ddgs: { results: rows } } },
  )
  assert.equal(meta.sources.length, 25)
  assert.equal(meta.truncated, false)
})

test('the citation card dedupes by URL and drops unsafe URLs', () => {
  const { stages } = setup()
  const meta = stages.tool.output.presentationMeta(
    { query: 'q' },
    {
      query: 'q',
      providers: {
        ddgs: {
          results: [
            { title: 'A', url: 'https://example.org/a', description: 'x' },
            { title: 'dupe', url: 'https://example.org/a/', description: 'y' },
            { title: 'B', url: 'https://example.org/b', description: 'z' },
          ],
        },
        exa: {
          results: [
            { title: 'Cross-provider dupe', url: 'https://example.org/a', description: 'again' },
            { title: 'Unsafe', url: 'javascript:alert(1)', description: 'no' },
          ],
        },
      },
    },
  )
  // Trailing-slash duplicates collapse; the unsafe javascript: row is gone.
  assert.deepEqual(meta.sources.map(source => source.url), [
    'https://example.org/a', 'https://example.org/b',
  ])
})

// The two remaining policy switches are the settings card's own design and must
// keep their exact behavior: URL dedupe collapses repeats, and the prose-answer
// switch only ever governs the card (never the core model payload).
test('turning URL dedupe off keeps every duplicate on the card', () => {
  const wrap = value => ({ get: () => value })
  const { stages } = setup({ cfg: config({ dedupeByUrl: wrap(false) }) })
  const meta = stages.tool.output.presentationMeta(
    { query: 'q' },
    {
      query: 'q',
      providers: {
        ddgs: {
          results: [
            { title: 'A', url: 'https://example.org/a', description: 'x' },
            { title: 'dupe', url: 'https://example.org/a/', description: 'y' },
          ],
        },
      },
    },
  )
  assert.deepEqual(meta.sources.map(source => source.url), [
    'https://example.org/a', 'https://example.org/a/',
  ])
})

test('the prose-answer switch governs the card only', async () => {
  const wrap = value => ({ get: () => value })
  const upstream = ({ query, providers }) => ({
    query,
    providers: { [providers[0]]: { answer: 'upstream prose', results: [] } },
  })
  const withAnswers = setup({ cfg: config({ includeAnswer: wrap(true) }), impl: upstream })
  const withoutAnswers = setup({ cfg: config({ includeAnswer: wrap(false) }), impl: upstream })

  const cardOn = withAnswers.stages.tool.output.presentationMeta(
    { query: 'q' },
    { query: 'q', providers: { ddgs: { answer: 'upstream prose', results: [] } } },
  )
  const cardOff = withoutAnswers.stages.tool.output.presentationMeta(
    { query: 'q' },
    { query: 'q', providers: { ddgs: { answer: 'upstream prose', results: [] } } },
  )
  assert.equal(cardOn.answer, 'upstream prose')
  assert.equal('answer' in cardOff, false)

  // Either way the model-facing payload keeps the provider answer, exactly as
  // the MCP operation does.
  const result = await withoutAnswers.stages.tool.execute({ query: 'q', providers: ['ddgs'] }, { signal: undefined })
  assert.deepEqual(result, {
    query: 'q',
    providers: { ddgs: { answer: 'upstream prose', results: [] } },
  })
})

test('the advertised max_results default and range match the Python operation', async () => {
  const { stages } = setup()
  const advertised = stages.tool.parameters.properties.max_results
  assert.equal(advertised.type, 'integer')

  // Read the core operation's own schema rather than restating the numbers, so
  // the two contracts cannot drift apart unnoticed.
  const core = readFileSync(new URL('../../../agent_web_search/schema.py', import.meta.url), 'utf8')
  const block = core.slice(core.indexOf('"max_results"'))
  assert.equal(advertised.default, Number(block.match(/"default":\s*(\d+)/)[1]))
  const maximum = Number(block.match(/"maximum":\s*(\d+)/)[1])
  assert.equal(Number(block.match(/"minimum":\s*(\d+)/)[1]), 1)

  // DSH's schema DSL cannot express numeric bounds, so the runtime carries them.
  await assert.rejects(
    stages.tool.execute({ query: 'q', max_results: maximum + 1 }, {}),
    new RegExp(`between 1 and ${maximum}`),
  )
})

test('renders the model-facing envelope as JSON text', () => {
  const { stages } = setup()
  const payload = {
    query: 'q',
    providers: { ddgs: { answer: 'a', results: [{ title: 'T', url: 'https://example.org/a', description: 'D' }] } },
  }
  assert.deepEqual(stages.tool.output.render({}, payload), [{ type: 'text', text: JSON.stringify(payload) }])
})

test('an all-providers-failed result draws no citation card', () => {
  const { stages } = setup()
  const failure = {
    error: { code: 'all_providers_failed', message: 'x', provider_errors: { ddgs: 'y' } },
    query: 'q',
  }
  // The envelope is returned as a *successful* value, so `isError` is false here:
  // presenting it would otherwise draw an empty "no sources" web card.
  const meta = stages.tool.output.presentationMeta({ query: 'q' }, failure)
  assert.equal(meta.failed, true)
  assert.deepEqual(meta.sources, [])
  assert.equal(stages.tool.presentResult({ query: 'q' }, { isError: false, meta }), undefined)
})

test('a successful result still draws its citation card', () => {
  const { stages } = setup()
  const value = {
    query: 'q',
    providers: { ddgs: { results: [{ title: 'T', url: 'https://example.org/a', description: 'D' }] } },
  }
  const meta = stages.tool.output.presentationMeta({ query: 'q' }, value)
  assert.equal('failed' in meta, false)
  const shown = stages.tool.presentResult({ query: 'q' }, { isError: false, meta })
  assert.equal(shown.card, 'web')
  assert.equal(shown.sources.length, 1)
  assert.match(shown.sources[0].title, /【来源：DuckDuckGo】/)
})
