/**
 * Per-agent `web_search` installation.
 *
 * Agent presets (standard/ptc/cordis) mount their own `tool-web` row, so the
 * shipped `{ queries }` tool is registered in preset scope — where it shadows
 * anything this bundle registers at host scope, in either mount order. Bundle
 * and profile patch layers cannot reach preset rows, so the only supported
 * override point is the agent scope itself: scoped registrations shadow
 * preset-scoped ones.
 *
 * This module follows the documented pattern (see dsh-tool-subagent): on
 * `agent/created`, inject `['tools', 'systemPrompt']` on `agent.ctx` and
 * register our MCP-consistent tool there. The injected fiber belongs to the
 * agent, so it unwinds with it; the per-agent map plus an owner effect cover
 * plugin unload. A listener must never throw: `agent/created` is serial and a
 * failure rolls back agent creation.
 *
 * @module dsh-agent-web-search/agent-tool
 */

import { registerWebSearchTool } from './tool.js'

/**
 * Install the MCP-consistent `web_search` tool into every live agent scope.
 *
 * @param {import('@deepseek-ai/cordis').Context} ctx - the plugin context.
 * @param {object} options - shared provider options.
 * @param {() => object} options.config - the loader-resolved plugin config.
 * @param {AgentWebSearchProvider} options.provider - the registered seam provider.
 */
export function installAgentTool(ctx, { config, provider }) {
  const agents = ctx.get('agents')
  if (agents === undefined) {
    ctx.logger?.warn?.('agent-web-search: agent registry unavailable; model tool installed at host scope only')
    return
  }
  const installed = new Map()
  const installFor = (agent) => {
    if (agent === undefined || agent === null || installed.has(agent)) return
    try {
      const fiber = agent.ctx.inject(['tools', 'systemPrompt'], (scoped) => {
        registerWebSearchTool(scoped, { config, provider, force: true })
      })
      installed.set(agent, fiber)
    } catch (error) {
      ctx.logger?.warn?.(`agent-web-search: per-agent tool install skipped: ${error instanceof Error ? error.message : String(error)}`)
    }
  }
  const disposeFor = (agent) => {
    const fiber = installed.get(agent)
    if (fiber === undefined) return
    installed.delete(agent)
    try {
      const result = fiber.dispose()
      if (result !== undefined && typeof result.catch === 'function') {
        result.catch((error) => {
          ctx.logger?.warn?.(`agent-web-search: per-agent tool removal failed: ${String(error)}`)
        })
      }
    } catch (error) {
      ctx.logger?.warn?.(`agent-web-search: per-agent tool removal failed: ${error instanceof Error ? error.message : String(error)}`)
    }
  }
  for (const agent of agents.list()) installFor(agent)
  ctx.on('agent/created', ({ agent }) => { installFor(agent) })
  ctx.on('agent/disposed', ({ agent }) => { disposeFor(agent) })
  ctx.effect(() => () => {
    for (const agent of [...installed.keys()]) disposeFor(agent)
  }, 'agent-web-search: agent tool installs')
}
