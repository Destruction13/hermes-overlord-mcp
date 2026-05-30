# Architecture

## Intent

Hermes Overlord MCP exposes one universal MCP surface for any client that can
launch a `stdio` process or connect to a Streamable HTTP endpoint. IDE-specific
behavior is limited to generated configuration snippets.

## Main execution paths

1. `npx` MCP path: the client launches `hermes-overlord-mcp`, which starts the
   Node MCP server over `stdio`.
2. Streamable HTTP path: `hermes-overlord-mcp start-http` starts a localhost MCP
   endpoint at `http://127.0.0.1:8765/mcp`.
3. Bridge path: MCP tools call `bridge.cli`, which invokes the configured Hermes
   runtime through `HERMES_BRIDGE_COMMAND`, `HERMES_PYTHON`, or the default
   Hermes runtime under `HERMES_HOME`.
4. Portable init path: `hermesctl.py init` creates `HERMES_HOME`, copies
   sanitized profile and skill templates, and writes a client config snippet.

## Runtime components

- MCP entrypoint: `bin/hermes-overlord-mcp.js`.
- Python bridge: `bridge/core.py` and `bridge/cli.py`.
- Optional Python MCP adapter: `mcp/hermes_overlord_mcp.py`.
- Distribution utility: `hermesctl.py`.
- Dashboard source: `dashboard/`.
- Sanitized templates: `dist/hermes-portable/runtime/` and selected skills.

## Client contract

The MCP client submits exactly one durable root task with `hermes_submit_task`,
then reads `hermes_task_report`, `hermes_task_status`, or
`hermes_task_events`. Hermes owns routing, specialists, tools, review,
watchdog, and synthesis.

## Evidence

- `bin/hermes-overlord-mcp.js`
- `bridge/core.py`
- `bridge/cli.py`
- `hermesctl.py`
- `README.md`
