# Conventions

## MCP conventions

- Keep the MCP server client-neutral. Add IDE-specific logic only to config
  generators or installer adapters.
- Use `hermes-overlord` as the server id and `Hermes Overlord` as the display
  name.
- Use `stdio` as the local default and Streamable HTTP only when a user asks for
  an endpoint.
- Keep HTTP bound to `127.0.0.1` unless explicit remote authentication and
  network controls are configured.

## Bridge conventions

- The external MCP client submits one durable root handoff. Hermes owns routing,
  specialist profiles, skills, MCP/tool usage, review, watchdog, and synthesis.
- Worker evidence must come from task runs, comments, events, logs, or exact MCP
  tool calls, not prompt text.
- Secrets must not be printed. Reports can state that a key is present, missing,
  invalid, or needs rotation.

## Package conventions

- Publish only allowlisted files through `package.json` `files`.
- Keep local history, logs, sessions, caches, screenshots, token stores,
  `node_modules`, and scratch work outside the package.
- Add new client support through `hermesctl.py mcp-config --client ...` and test
  that the generated JSON parses.

## Evidence

- `package.json`
- `hermesctl.py`
- `bridge/core.py`
- `bin/hermes-overlord-mcp.js`
