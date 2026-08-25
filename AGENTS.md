# Agent instructions

Read `ARCHITECTURE.md` before changing transports, configuration,
authentication, deployment, providers, tool schemas, or public entry points.

Non-negotiable invariants:

- Keep one `SearchEngine` and one shared MCP server definition.
- Keep `agent-web-search-mcp` as the single MCP command; stdio is its default
  and HTTP is a transport mode.
- Keep MCP HTTP stateless, JSON-response based, and authenticated by default.
- Keep runtime configuration environment-only; do not add an application
  configuration file.
- Keep stdio and HTTP tool schemas, result shapes, and error semantics equal.
- Keep provider credentials server-side and out of MCP tool arguments.
- Keep deployment-specific code limited to thin launch adapters.
- Do not add REST, OAuth, multi-tenancy, or persistent sessions without an
  explicit architecture decision from the project owner.

Update `ARCHITECTURE.md` in the same change whenever an approved decision
changes one of these invariants.
