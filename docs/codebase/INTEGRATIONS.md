# Integrations

## MCP clients

Hermes Overlord MCP is not tied to one IDE. The core server is the same for all
clients, and `hermesctl.py mcp-config` generates snippets for these targets:

- `generic`
- `vscode`
- `cursor`
- `kilo`
- `kiro`
- `windsurf`
- `opencode`
- `codex`
- `antigravity`

Unknown clients can use the `generic` `mcpServers` snippet if they support
local `stdio` MCP servers.

VS Code-style clients that expose `--add-mcp`, including VS Code, Cursor, Kiro,
and Antigravity, can use `hermesctl.py mcp-config --client <client> --format
add-mcp` to generate the flat install payload accepted by that CLI flag.

## Hermes gateways

The bridge delegates real work to the configured Hermes runtime. The runtime can
be selected with `HERMES_BRIDGE_COMMAND`, `HERMES_PYTHON`, or the default Hermes
installation under `HERMES_HOME`.

Provider and MCP credentials remain user-supplied. The package exports
`ENV_KEYS.txt` files with required variable names only.

## Dashboard integrations

`hermes-site.ps1` serves `dashboard/serve-dashboard.py` for local operators.
`overlord-dashboard.ps1` starts the native Hermes dashboard when the Hermes
runtime is installed.

## Codex-specific support

Codex `/hermes` guardrails and reliability scripts remain in `mcp/` as a
compatibility layer. They are not the universal installation model and don't
change the client-neutral MCP contract.

## Evidence

- `hermesctl.py`
- `bin/hermes-overlord-mcp.js`
- `docs/distribution/README.md`
