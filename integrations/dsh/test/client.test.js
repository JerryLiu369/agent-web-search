import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'

const file = new URL('../lib/client.js', import.meta.url)
const React = {
  createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }),
  useState: initial => [initial, () => {}],
  useEffect: () => {},
}
const all = node => Array.isArray(node) ? node.flatMap(all) : !node || typeof node !== 'object' ? [] : [node, ...(node.children ?? []).flatMap(all)]
const strings = node => all(node).flatMap(entry => (entry.children ?? []).filter(child => typeof child === 'string'))

/**
 * Stand-in for DSH's own web card. The harness records elements instead of
 * rendering them, so the shipped component is represented as a host tag: what
 * gets asserted is the props we hand it, which is the part this bundle owns
 * (the shipped component renders itself, and DSH already tests that).
 */
const primitives = {
  WebBlock: 'ds-web-block',
  IconGlobeOutlineRegular: 'ds-globe-icon',
}

function load(fetchImpl = () => { throw new Error('unexpected fetch') }, options = {}) {
  let mod
  runInNewContext(readFileSync(file, 'utf8'), {
    window: { __ModuleLoader__: { load: definition => { mod = definition.factory(name => {
      if (name === 'react') return React
      if (name === '@deepseek-ai/dsh-client-ui-primitives') {
        // A deployment whose client loader does not register the package must not
        // break the rest of the client half.
        if (options.noPrimitives === true) throw new Error(`unregistered client module: ${name}`)
        return primitives
      }
      throw new Error(`unexpected client module: ${name}`)
    }) } } },
    crypto: { randomUUID: () => '12345678-abcd-4def-8000-123456789012' },
    URL, Object, Set, Map, Promise, console, fetch: fetchImpl,
  }, { filename: 'client.js' })
  return mod
}

function mounted(fetchImpl, options = {}) {
  const requests = []
  const credentialsWrites = []
  const plugin = load(fetchImpl, options)
  const registrations = []
  const writes = []
  const value = {
    mode: 'fanout', attemptTimeoutMs: 12000, totalTimeoutMs: 30000,
    dedupeByUrl: true, includeAnswer: true,
    providers: options.providers ?? [{ kind: 'retired_source', enabled: true, baseURL: 'http://127.0.0.1:8045/v1beta' }],
  }
  const scope = {
    subscribe: () => () => {},
    getSnapshot: () => ({ value, writable: true, status: 'ready' }),
    set: async (name, next) => { writes.push([name, next]); value[name] = next; return true },
    unset: async () => true,
  }
  const ctx = {
    locale: { bind: () => key => key, register: () => () => {} },
    configForms: { get: () => scope, whileServed: (_, cb) => (options.served === false ? undefined : cb()) },
    effect: cb => cb(),
    slots: { inject: (_, cb) => cb(), register: (definition, component) => {
      registrations.push({ definition, component })
      return () => {}
    } },
    remote: { $on: () => () => {}, credentials: {
      describe: async () => ({ ok: true, value: options.credentials ?? {} }),
      set: async (ref, text) => { credentialsWrites.push({ ref, text }); return { ok: options.rejectCredentials !== true } },
    } },
  }
  plugin.apply(ctx)
  // Registration order is not part of the contract: the settings section is the
  // one that exposes `inject`, and the web row may be registered before it. When
  // the namespace is not served there is no section at all.
  const section = registrations.find(item => item.definition.name === 'settings.section')
  return { registrations, injected: section?.definition.inject(), writes, requests, credentialsWrites }
}

function view(registration, injected, tab, snapshot) {
  const original = React.useState
  React.useState = initial => [typeof initial === 'string' ? tab : typeof initial === 'boolean' ? true : initial, () => {}]
  try {
    return registration.component({ ...injected, t: key => key, useAgentWebSearch: selector => selector(snapshot) })
  } finally { React.useState = original }
}

test('retired sources disappear from the queue and the sources tab', async () => {
  const { registrations, injected } = mounted()
  const section = registrations.find(item => item.definition.name === 'settings.section')
  assert.deepEqual(registrations.map(item => item.definition.name).sort(), ['settings.section', 'tool.call.toolview'])
  assert.equal(injected.hooks.agentWebSearch.getSnapshot().queue.some(item => item.kind === 'retired_source'), false)
  const sources = view(section, injected, 'sources', injected.hooks.agentWebSearch.getSnapshot())
  assert.equal(all(sources).some(node => node.type?.name === 'UpstreamRow' && node.props.entry.kind === 'retired_source'), false)
  assert.equal(sources.props.style.maxWidth, '920px')
})

test('activity renders exactly one table row per search call with inline attempts', () => {
  const { registrations, injected } = mounted()
  const section = registrations.find(item => item.definition.name === 'settings.section')
  const activity = view(section, injected, 'activity', injected.hooks.agentWebSearch.getSnapshot())
  const panel = all(activity).find(node => node.type?.name === 'SearchHistoryPanel')
  const original = React.useState
  React.useState = initial => [initial && Array.isArray(initial.entries)
    ? { entries: [{ id: 1, at: '2026-09-29T12:00:00Z', mode: 'fanout', status: 'success', resultCount: 5, durationMs: 1234, attempts: [
      { kind: 'exa', status: 'success', resultCount: 5, durationMs: 700 },
      { kind: 'parallel', status: 'timeout', resultCount: 0, durationMs: 1200, httpStatus: 504 },
    ] }], selectedProvider: 'agent-web-search', loading: false, error: false }
    : initial, () => {}]
  try {
    const rendered = panel.type(panel.props)
    const rows = all(rendered).filter(node => node.type === 'tr')
    assert.equal(rows.length, 2) // one header row and one call row
    const cells = all(rows[1]).filter(node => node.type === 'td')
    assert.equal(cells.length, 5)
    assert.match(cells[4].children[0], /Exa.*Parallel.*HTTP 504/)
    assert.equal(all(rows[1]).filter(node => node.type === 'p').length, 0)
    assert.equal(cells[4].props.style.whiteSpace, 'nowrap')
    assert.equal(all(rendered).find(node => node.props?.role === 'region').props.style.overflow, 'auto')
  } finally { React.useState = original }
})

test('model text is staged per upstream and saved only when non-blank', async () => {
  const { injected, writes } = mounted()
  injected.setModels('deepseek', 'deepseek-v4-flash')
  injected.setEnabled('deepseek', true)
  injected.setModels('exa', '   ')
  injected.setEnabled('exa', true)
  await injected.save()
  const saved = writes.find(([field]) => field === 'providers')[1]
  assert.equal(saved.find(item => item.kind === 'deepseek').models, 'deepseek-v4-flash')
  assert.equal('models' in saved.find(item => item.kind === 'exa'), false)
})


test('tool type/name are staged per upstream and saved only when non-blank', async () => {
  const { injected, writes } = mounted()
  injected.setToolType('messages', 'web_search_20250101')
  injected.setToolName('messages', 'custom_search')
  injected.setEnabled('messages', true)
  injected.setToolType('responses', '   ')
  injected.setEnabled('responses', true)
  await injected.save()
  const saved = writes.find(([field]) => field === 'providers')[1]
  assert.equal(saved.find(item => item.kind === 'messages').toolType, 'web_search_20250101')
  assert.equal(saved.find(item => item.kind === 'messages').toolName, 'custom_search')
  assert.equal('toolType' in saved.find(item => item.kind === 'responses'), false)
})

// The shipped web row only builds a citation card when a call carries its own
// `{ queries }` array, which this plugin deliberately does not use, so the
// plugin registers its own view for the `web_search` key.
function webRow(options = {}) {
  const { registrations } = mounted(undefined, options)
  const row = registrations.find(item => item.definition.name === 'tool.call.toolview')
  assert.ok(row, 'expected a tool.call.toolview registration')
  return row
}

function renderRow(row, { block, phase = 'result', expanded = true }) {
  return row.component({
    t: key => key,
    block,
    phase,
    useDisclosure: () => ({ expanded, toggle: () => {} }),
  })
}

function settledBlock(overrides = {}) {
  return {
    kind: 'tool-result',
    callId: 'call_1',
    call: { name: 'web_search', argsRaw: JSON.stringify({ query: '中文查询', providers: ['ddgs'], max_results: 2 }) },
    isError: false,
    content: [{ type: 'text', text: '{"query":"中文查询","providers":{}}' }],
    meta: {
      sources: [
        { url: 'https://example.org/a', title: '【来源：DuckDuckGo】 A', snippet: '摘要 A' },
        { url: 'https://example.org/b', title: '【来源：DuckDuckGo】 B' },
      ],
      truncated: false,
    },
    ...overrides,
  }
}

test('claims the web_search view so the citation card can render', () => {
  const row = webRow()
  assert.equal(row.definition.key, 'web_search')
  assert.equal(row.definition.locale, 'agent-web-search')
  // The shipped row keeps this key at priority 0, and re-registering the same
  // key at the same priority throws — a lower priority is how the slot ledger
  // says to shadow it, regardless of registration order.
  assert.equal(row.definition.priority, -1)
})

test('the view is registered even while the settings namespace is not served', () => {
  const { registrations } = mounted(undefined, { served: false })
  assert.equal(registrations.some(item => item.definition.name === 'tool.call.toolview'), true)
  assert.equal(registrations.some(item => item.definition.name === 'settings.section'), false)
})

test('a settled search hands the sources to the shipped web block', () => {
  const rendered = renderRow(webRow(), { block: settledBlock() })
  const nodes = all(rendered)
  const web = nodes.find(node => node.type === 'ds-web-block')
  assert.ok(web, 'expected the shipped WebBlock to receive the card body')
  assert.equal(web.props.kind, 'search')
  assert.equal(web.props.truncated, false)
  assert.deepEqual(web.props.sources.map(source => source.url), ['https://example.org/a', 'https://example.org/b'])
  assert.deepEqual(web.props.sources.map(source => source.title), ['【来源：DuckDuckGo】 A', '【来源：DuckDuckGo】 B'])
  assert.equal(web.props.sources[0].snippet, '摘要 A')
  // The shipped icon comes from the same package.
  assert.equal(nodes.some(node => node.type === 'ds-globe-icon'), true)
  // The row keeps our own title and the call's query, and hides the raw JSON.
  const text = strings(rendered)
  assert.equal(text.includes('cardTitle'), true)
  assert.equal(text.includes('中文查询'), true)
  assert.equal(text.includes('2 resultUnit'), true)
  assert.equal(nodes.some(node => node.type === 'pre'), false)
})

test('the answer is rendered by the row, not handed to the web block', () => {
  const block = settledBlock()
  block.meta.answer = '上游成文答案'
  const rendered = renderRow(webRow(), { block })
  assert.equal(strings(rendered).includes('上游成文答案'), true)
  const web = all(rendered).find(node => node.type === 'ds-web-block')
  // Keeping `answer` out of WebBlock is what lets the search body skip the
  // conversation namespace's markdown label bundle.
  assert.equal('answer' in web.props, false)
})

test('a truncated card keeps the shipped truncation notice', () => {
  const block = settledBlock()
  block.meta.truncated = true
  const rendered = renderRow(webRow(), { block })
  const web = all(rendered).find(node => node.type === 'ds-web-block')
  assert.equal(web.props.truncated, true)
  assert.equal(web.props.labels.sourcesTruncated, 'cardTruncated')
  assert.equal(web.props.labels.noResults, 'cardEmpty')
})

test('a failed search falls back to the recorded error text', () => {
  const block = settledBlock({ isError: true, error: { message: '搜索失败原因' }, meta: undefined })
  const rendered = renderRow(webRow(), { block })
  const nodes = all(rendered)
  const pre = nodes.find(node => node.type === 'pre')
  assert.ok(pre, 'expected the raw fallback')
  assert.deepEqual(pre.children, ['搜索失败原因'])
  assert.equal(strings(rendered).includes('cardFailed'), true)
})

test('a result without card metadata falls back to the raw output', () => {
  const block = settledBlock({ meta: undefined })
  const rendered = renderRow(webRow(), { block })
  const pre = all(rendered).find(node => node.type === 'pre')
  assert.ok(pre, 'expected the raw fallback')
  assert.equal(String(pre.children[0]).includes('"query"'), true)
  assert.equal(all(rendered).some(node => node.type === 'ds-web-block'), false)
})

test('a running call renders without arguments or a card', () => {
  const rendered = renderRow(webRow(), { block: { phase: 'preparing', callId: 'call_1' }, phase: 'preparing', expanded: false })
  assert.equal(strings(rendered).includes('cardRunning'), true)
  assert.equal(all(rendered).some(node => node.type === 'pre'), false)
})

test('the layer still renders the sources when the shipped web block is missing', () => {
  const rendered = renderRow(webRow({ noPrimitives: true }), { block: settledBlock() })
  const nodes = all(rendered)
  assert.equal(nodes.some(node => node.type === 'ds-web-block'), false)
  assert.deepEqual(
    nodes.filter(node => node.type === 'a').map(node => node.props.href),
    ['https://example.org/a', 'https://example.org/b'],
  )
  assert.equal(strings(rendered).includes('摘要 A'), true)
})
