import test from 'node:test'
import assert from 'node:assert/strict'
import { EventEmitter } from 'node:events'
import { PassThrough } from 'node:stream'
import { PythonSearchBridge } from '../lib/bridge.js'

class FakeChild extends EventEmitter {
  constructor(handler) {
    super()
    this.stdout = new PassThrough()
    this.stderr = new PassThrough()
    this.stdin = new PassThrough()
    this.killed = false
    this.calls = []
    this.input = Buffer.alloc(0)
    this.stdin.on('data', chunk => {
      this.input = Buffer.concat([this.input, chunk])
      for (;;) {
        const text = this.#nextRequest()
        if (text === undefined) return
        if (text.length === 0) continue
        handler(JSON.parse(text), this)
      }
    })
  }

  /**
   * Read one request frame, auto-detecting line framing versus
   * `Content-Length` framing so the bridge can be driven in either mode.
   */
  #nextRequest() {
    if (this.input.length >= 15 && /^content-length:/i.test(this.input.subarray(0, 15).toString('latin1'))) {
      const headerEnd = this.input.indexOf('\r\n\r\n')
      if (headerEnd < 0) return undefined
      const match = this.input.subarray(0, headerEnd).toString('latin1').match(/content-length:\s*(\d+)/i)
      if (!match) throw new Error('fake child received malformed headers')
      const start = headerEnd + 4
      const length = Number(match[1])
      if (this.input.length - start < length) return undefined
      const body = this.input.subarray(start, start + length).toString('utf8')
      this.input = this.input.subarray(start + length)
      return body
    }
    const newline = this.input.indexOf(0x0a)
    if (newline < 0) return undefined
    const line = this.input.subarray(0, newline).toString('utf8')
    this.input = this.input.subarray(newline + 1)
    return line
  }

  reply(message) {
    this.stdout.write(`${JSON.stringify(message)}\n`)
  }

  kill() {
    this.killed = true
    this.emit('exit', 0, 'SIGTERM')
    return true
  }
}

function spawnFor(handler, state) {
  return () => {
    const child = new FakeChild(handler)
    state.child = child
    return child
  }
}

function replyToCalls(payload, calls) {
  return (message, child) => {
    calls.push(message)
    if (message.method === 'initialize') {
      child.reply({ jsonrpc: '2.0', id: message.id, result: { protocolVersion: '2025-06-18' } })
    } else if (message.method === 'tools/call') {
      const response = payload?.error
        ? payload
        : { query: message.params.arguments.query, ...payload }
      child.reply({ jsonrpc: '2.0', id: message.id, result: { content: [{ type: 'text', text: JSON.stringify(response) }] } })
    }
  }
}

test('bridge calls only web_search, propagates maxResults, preserves the native payload, and cleans up', async () => {
  const state = {}
  const calls = []
  let childEnvironment
  const bridge = new PythonSearchBridge({
    command: 'fake-agent-web-search-mcp',
    spawn: (command, args, options) => {
      childEnvironment = options.env
      return spawnFor(replyToCalls({ providers: { exa: { answer: 'answer', results: [{ title: 'A', url: 'https://example.org/a', description: 'summary', published_at: '2025-01-02', author: 'Author' }] } } }, calls), state)(command, args, options)
    },
    env: { PATH: '/bin' }, lineMode: true,
  })
  const result = await bridge.search({
    query: 'latest question', maxResults: 2, providers: ['exa'],
    entries: [{ kind: 'exa', credentialRef: 'EXA_API_KEY' }],
    resolveValue: async () => 'PRIVATE_KEY', timeoutMs: 1000,
  })
  assert.equal(calls.filter(call => call.method === 'tools/call').length, 1)
  assert.equal(childEnvironment.AGENT_WEB_SEARCH_PROVIDERS, 'exa')
  assert.equal(childEnvironment.AGENT_WEB_SEARCH_MCP_TRANSPORT, 'stdio')
  assert.equal(childEnvironment.EXA_API_KEY, 'PRIVATE_KEY')
  assert.equal(JSON.stringify(calls).includes('PRIVATE_KEY'), false)
  assert.deepEqual(calls.find(call => call.method === 'tools/call').params, {
    name: 'web_search', arguments: { query: 'latest question', max_results: 2, providers: ['exa'] },
  })
  assert.deepEqual(result, {
    query: 'latest question',
    providers: {
      exa: {
        answer: 'answer',
        results: [{
          title: 'A', url: 'https://example.org/a', description: 'summary',
          published_at: '2025-01-02', author: 'Author',
        }],
      },
    },
  })
  assert.equal(state.child.killed, true)
})

test('bridge omits max_results so the core default applies when the caller does not set one', async () => {
  const state = {}
  const calls = []
  const bridge = new PythonSearchBridge({
    spawn: (command, args, options) => spawnFor(replyToCalls({ providers: { exa: { results: [] } } }, calls), state)(command, args, options),
    env: {}, lineMode: true,
  })
  await bridge.search({
    query: 'q', providers: ['exa'], entries: [{ kind: 'exa' }],
    resolveValue: async () => undefined, timeoutMs: 1000,
  })
  assert.deepEqual(calls.find(call => call.method === 'tools/call').params.arguments, {
    query: 'q', providers: ['exa'],
  })
})

test('bridge strips inherited provider endpoint overrides before spawning', async () => {
  const state = {}
  const calls = []
  let childEnvironment
  const bridge = new PythonSearchBridge({
    spawn: (command, args, options) => {
      childEnvironment = options.env
      return spawnFor(replyToCalls({ providers: { exa: { results: [{ title: 'A', url: 'https://example.org/a', description: 'summary' }] } } }, calls), state)(command, args, options)
    },
    env: {
      AGENT_WEB_SEARCH_EXA_ENDPOINT: 'https://stale.example/exa',
      AGENT_WEB_SEARCH_PARALLEL_MCP_URL: 'https://stale.example/parallel',
      EXA_MCP_URL: 'https://stale.example/mcp',
    },
    lineMode: true,
  })
  await bridge.search({
    query: 'q', maxResults: 1, providers: ['exa'], entries: [{ kind: 'exa' }],
    resolveValue: async () => undefined, timeoutMs: 1000,
  })
  assert.equal(childEnvironment.AGENT_WEB_SEARCH_EXA_ENDPOINT, undefined)
  assert.equal(childEnvironment.AGENT_WEB_SEARCH_PARALLEL_MCP_URL, undefined)
  assert.equal(childEnvironment.EXA_MCP_URL, undefined)
})

test('bridge propagates structured all-provider failure without raw bodies', async () => {
  const state = {}
  const bridge = new PythonSearchBridge({
    spawn: spawnFor(replyToCalls({ error: { code: 'all_providers_failed', provider_errors: { ddgs: 'ddgs RuntimeError' } } }, []), state),
    env: {}, lineMode: true,
  })
  await assert.rejects(bridge.search({
    query: 'q', maxResults: 4, providers: ['ddgs'], entries: [{ kind: 'ddgs' }],
    resolveValue: async () => undefined, timeoutMs: 1000,
  }), error => {
    assert.equal(error.code, 'all_providers_failed')
    assert.deepEqual(error.providerErrors, { ddgs: 'ddgs RuntimeError' })
    assert.equal(error.message.includes('RuntimeError'), false)
    return true
  })
})

test('bridge rejects malformed MCP results and bounds process output', async () => {
  const childState = {}
  const child = new PythonSearchBridge({
    spawn: spawnFor((message, process) => {
      if (message.method === 'initialize') process.reply({ jsonrpc: '2.0', id: message.id, result: {} })
      if (message.method === 'tools/call') process.stdout.write('{not-json}\n')
    }, childState), env: {}, lineMode: true,
  })
  await assert.rejects(child.search({ query: 'q', maxResults: 1, providers: ['ddgs'], entries: [{ kind: 'ddgs' }], resolveValue: async () => undefined, timeoutMs: 1000 }), error => error.code === 'malformed_result')

  const largeState = {}
  const large = new PythonSearchBridge({
    spawn: spawnFor((_message, process) => process.stdout.write('x'.repeat(1024 * 1024 + 1)), largeState), env: {}, lineMode: true,
  })
  await assert.rejects(large.search({ query: 'q', maxResults: 1, providers: ['ddgs'], entries: [{ kind: 'ddgs' }], resolveValue: async () => undefined, timeoutMs: 1000 }), error => error.code === 'output_limit')
  assert.equal(largeState.child.killed, true)
})

test('bridge cancellation and timeout terminate the child process', async () => {
  const cancellationState = {}
  const cancellation = new PythonSearchBridge({
    spawn: spawnFor(() => {}, cancellationState), env: {}, lineMode: true,
  })
  const controller = new AbortController()
  const pending = cancellation.search({ query: 'q', maxResults: 1, providers: ['ddgs'], entries: [{ kind: 'ddgs' }], resolveValue: async () => undefined, timeoutMs: 5000, signal: controller.signal })
  controller.abort()
  await assert.rejects(pending, error => error.name === 'AbortError')
  assert.equal(cancellationState.child.killed, true)

  const timeoutState = {}
  const timeout = new PythonSearchBridge({ spawn: spawnFor(() => {}, timeoutState), env: {}, lineMode: true })
  await assert.rejects(timeout.search({ query: 'q', maxResults: 1, providers: ['ddgs'], entries: [{ kind: 'ddgs' }], resolveValue: async () => undefined, timeoutMs: 10 }), error => error.name === 'TimeoutError')
  assert.equal(timeoutState.child.killed, true)
})

test('bridge forwards per-source models and clears inherited model vars', async () => {
  const state = {}
  const calls = []
  let childEnvironment
  const bridge = new PythonSearchBridge({
    command: 'fake-agent-web-search-mcp',
    spawn: (command, args, options) => {
      childEnvironment = options.env
      return spawnFor(replyToCalls({ providers: { deepseek: { results: [{ title: 'A', url: 'https://example.org/a', description: 'summary' }] } } }, calls), state)(command, args, options)
    },
    env: { PATH: '/bin', AGENT_WEB_SEARCH_DEEPSEEK_MODELS: 'stale-model', AGENT_WEB_SEARCH_GEMINI_MODELS: 'stale-model' }, lineMode: true,
  })
  const result = await bridge.search({
    query: 'q', maxResults: 1, providers: ['deepseek'],
    entries: [{ kind: 'deepseek', credentialRef: 'DEEPSEEK_API_KEY', models: 'deepseek-v4-flash, deepseek-v4-pro' }],
    resolveValue: async () => undefined, timeoutMs: 1000,
  })
  assert.equal(childEnvironment.AGENT_WEB_SEARCH_DEEPSEEK_MODELS, 'deepseek-v4-flash, deepseek-v4-pro')
  assert.equal(childEnvironment.AGENT_WEB_SEARCH_GEMINI_MODELS, undefined)
  assert.equal(result.providers.deepseek.results.length, 1)
})

test('bridge passes time_range to the MCP call only when configured', async () => {
  for (const [timeRange, expected] of [['w', 'w'], [undefined, undefined], ['', undefined]]) {
    const state = {}
    const calls = []
    const bridge = new PythonSearchBridge({
      spawn: spawnFor(replyToCalls({ providers: { ddgs: { results: [{ title: 'A', url: 'https://example.org/a', description: 'summary' }] } } }, calls), state),
      env: {}, lineMode: true,
    })
    await bridge.search({
      query: 'q', maxResults: 1, providers: ['ddgs'], entries: [{ kind: 'ddgs' }],
      resolveValue: async () => undefined, timeoutMs: 1000, timeRange,
    })
    const params = calls.find(call => call.method === 'tools/call').params
    assert.equal(params.arguments.time_range ?? undefined, expected)
  }
})

test('bridge forwards tool type/name overrides and clears inherited ones', async () => {
  const state = {}
  const calls = []
  let childEnvironment
  const bridge = new PythonSearchBridge({
    command: 'fake-agent-web-search-mcp',
    spawn: (command, args, options) => {
      childEnvironment = options.env
      return spawnFor(replyToCalls({ providers: { messages: { results: [{ title: 'A', url: 'https://example.org/a', description: 'summary' }] } } }, calls), state)(command, args, options)
    },
    env: { PATH: '/bin', AGENT_WEB_SEARCH_MESSAGES_TOOL_TYPE: 'stale-type', AGENT_WEB_SEARCH_RESPONSES_TOOL_TYPE: 'stale-type' }, lineMode: true,
  })
  await bridge.search({
    query: 'q', maxResults: 1, providers: ['messages'],
    entries: [{ kind: 'messages', credentialRef: 'AGENT_WEB_SEARCH_MESSAGES_API_KEY', toolType: 'web_search_20250101', toolName: 'custom_search' }],
    resolveValue: async () => undefined, timeoutMs: 1000,
  })
  assert.equal(childEnvironment.AGENT_WEB_SEARCH_MESSAGES_TOOL_TYPE, 'web_search_20250101')
  assert.equal(childEnvironment.AGENT_WEB_SEARCH_MESSAGES_TOOL_NAME, 'custom_search')
  assert.equal(childEnvironment.AGENT_WEB_SEARCH_RESPONSES_TOOL_TYPE, undefined)
})

test('bridge sends grok_search_mode only on grok attempts', async () => {
  for (const [kind, grokMode, expected] of [['grok', 'x_search', 'x_search'], ['grok', '', undefined], ['ddgs', 'both', undefined]]) {
    const state = {}
    const calls = []
    const bridge = new PythonSearchBridge({
      spawn: spawnFor(replyToCalls({ providers: { [kind]: { results: [{ title: 'A', url: 'https://example.org/a', description: 'summary' }] } } }, calls), state),
      env: {}, lineMode: true,
    })
    await bridge.search({
      query: 'q', maxResults: 1, providers: [kind], entries: [{ kind }],
      resolveValue: async () => undefined, timeoutMs: 1000, grokMode,
    })
    const params = calls.find(call => call.method === 'tools/call').params
    assert.equal(params.arguments.grok_search_mode ?? undefined, expected)
  }
})

// A multi-byte UTF-8 sequence can straddle two stdout chunks. Decoding each
// chunk on its own would corrupt both halves into U+FFFD, silently mangling CJK
// titles, descriptions and answers in the model payload and the citation card.
const CJK_PAYLOAD = {
  query: '中文查询',
  providers: {
    exa: {
      answer: '中文答案 🚀',
      results: [{ title: '中文标题 🚀 结尾', url: 'https://example.org/中文路径', description: '中文摘要 🚀' }],
    },
  },
}

function framed(message, lineMode) {
  const body = `${JSON.stringify(message)}\n`
  return lineMode ? Buffer.from(body, 'utf8') : Buffer.concat([
    Buffer.from(`Content-Length: ${Buffer.byteLength(body)}\r\n\r\n`, 'latin1'),
    Buffer.from(body, 'utf8'),
  ])
}

function splitMidCharacter(buffer) {
  // Split one byte into the first multi-byte character, so the reader sees a
  // truncated UTF-8 sequence; ASCII-only frames just split in the middle.
  const index = buffer.indexOf(Buffer.from('中', 'utf8'))
  const at = index < 0 ? Math.floor(buffer.length / 2) : index + 1
  return [buffer.subarray(0, at), buffer.subarray(at)]
}

async function searchWithSplitReply({ lineMode }) {
  const state = {}
  const replySplit = async (child, message) => {
    const [head, tail] = splitMidCharacter(framed(message, lineMode))
    child.stdout.write(head)
    // Yield so the reader sees the truncated frame first, which is exactly the
    // boundary condition being guarded against.
    await new Promise(resolve => setImmediate(resolve))
    child.stdout.write(tail)
  }
  const bridge = new PythonSearchBridge({
    spawn: spawnFor(async (message, child) => {
      if (message.method === 'initialize') {
        await replySplit(child, { jsonrpc: '2.0', id: message.id, result: { protocolVersion: '2025-06-18' } })
        return
      }
      if (message.method !== 'tools/call') return
      await replySplit(child, {
        jsonrpc: '2.0', id: message.id,
        result: { content: [{ type: 'text', text: JSON.stringify(CJK_PAYLOAD) }] },
      })
    }, state),
    env: {}, lineMode,
  })
  return bridge.search({
    query: 'q', providers: ['exa'], entries: [{ kind: 'exa' }],
    resolveValue: async () => undefined, timeoutMs: 5000,
  })
}

test('line-framed replies keep multi-byte characters split across chunks intact', async () => {
  const result = await searchWithSplitReply({ lineMode: true })
  assert.deepEqual(result, CJK_PAYLOAD)
  assert.equal(JSON.stringify(result).includes('\uFFFD'), false)
})

test('content-length-framed replies keep multi-byte characters split across chunks intact', async () => {
  const result = await searchWithSplitReply({ lineMode: false })
  assert.deepEqual(result, CJK_PAYLOAD)
  assert.equal(JSON.stringify(result).includes('\uFFFD'), false)
})
