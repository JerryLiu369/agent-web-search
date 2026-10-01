import test from 'node:test'
import assert from 'node:assert/strict'
import { installAgentTool } from '../lib/agent-tool.js'

function config() {
  const wrap = value => ({ get: () => value })
  return {
    mode: wrap('fanout'),
    providers: wrap([{ kind: 'ddgs', enabled: true, baseURL: '' }]),
    attemptTimeoutMs: wrap(2000), totalTimeoutMs: wrap(5000),
    dedupeByUrl: wrap(true), includeAnswer: wrap(false),
  }
}

const provider = {
  search: async () => ({ sources: [], truncated: false }),
}

function scopedTools(native) {
  const map = new Map(native ? [['web_search', { name: 'web_search', native: true }]] : [])
  return {
    map,
    get: name => map.get(name),
    register: definition => { map.set(definition.name, definition); return () => { map.delete(definition.name) } },
  }
}

function makeAgent({ native = false, broken = false } = {}) {
  const tools = scopedTools(native)
  const fibers = []
  return {
    agent: {
      id: Math.random().toString(36).slice(2),
      session: {},
      ctx: {
        inject: (deps, cb) => {
          assert.deepEqual(deps, ['tools', 'systemPrompt'])
          if (broken) throw new Error('no tools service here')
          const fiber = { disposed: false, dispose() { this.disposed = true } }
          fibers.push(fiber)
          cb({
            tools,
            systemPrompt: { section: () => {}, getSectionOrder: () => 0 },
            logger: {},
          })
          return fiber
        },
      },
    },
    tools,
    fibers,
  }
}

function setup({ live = [], service = true } = {}) {
  const listeners = {}
  const cleanups = []
  const warnings = []
  const ctx = {
    get: name => (name === 'agents' && service ? { list: () => [...live] } : undefined),
    on: (event, cb) => { (listeners[event] ??= []).push(cb) },
    effect: cb => { cleanups.push(cb); return () => {} },
    logger: { warn: message => warnings.push(message) },
  }
  installAgentTool(ctx, { config, provider })
  return { listeners, cleanups, warnings }
}

test('installs into live agents and shadows the preset-native tool', () => {
  const scope = makeAgent({ native: true })
  setup({ live: [scope.agent] })
  const installed = scope.tools.map.get('web_search')
  assert.equal(installed.native, undefined)
  assert.equal(installed.description.includes('Grok X-search modes'), true)
})

test('agent/created installs into newcomers; disposed unwinds', () => {
  const first = makeAgent({ native: true })
  const { listeners } = setup({ live: [first.agent] })
  assert.equal(first.tools.map.get('web_search').native, undefined)
  const second = makeAgent({ native: true })
  for (const cb of listeners['agent/created']) cb({ agent: second.agent })
  assert.equal(second.tools.map.get('web_search').native, undefined)
  for (const cb of listeners['agent/disposed']) cb({ agent: first.agent })
  assert.equal(first.fibers.length, 1)
  assert.equal(first.fibers[0].disposed, true)
})

test('a failing install never throws out of the serial listener', () => {
  const scope = makeAgent({ broken: true })
  const { listeners, warnings } = setup()
  for (const cb of listeners['agent/created']) cb({ agent: scope.agent })
  assert.match(warnings.join('\n'), /per-agent tool install skipped/)
})

test('missing agent registry warns once and keeps host behavior', () => {
  const { listeners, warnings } = setup({ service: false })
  assert.deepEqual(Object.keys(listeners), [])
  assert.match(warnings.join('\n'), /agent registry unavailable/)
})

test('owner effect cleanup disposes every installed scope', () => {
  const one = makeAgent()
  const two = makeAgent()
  const { cleanups } = setup({ live: [one.agent, two.agent] })
  assert.equal(cleanups.length, 1)
  cleanups[0]()()
  assert.equal(one.fibers[0].disposed, true)
  assert.equal(two.fibers[0].disposed, true)
})
