# Stack

## Summary

Hermes Overlord MCP is a client-neutral control package for a local Hermes
Overlord agent family. The package provides an `npx` launcher, MCP tools,
configuration generators, PowerShell wrappers, dashboard source, sanitized
profile templates, and selected skills. Runtime state remains outside the
package under `HERMES_HOME`.

## Languages and runtime

- Node.js: `bin/hermes-overlord-mcp.js` is the `npx` entrypoint and the primary
  MCP `stdio` server.
- Python: `bridge/`, `hermesctl.py`, dashboard utilities, and the optional
  FastMCP adapter under `mcp/`.
- PowerShell: local wrappers for Windows operators and legacy Codex-specific
  fallback scripts.
- JavaScript, CSS, and HTML: dashboard files in `dashboard/`.
- YAML and Markdown: sanitized profile templates and documentation.

## Dependencies

- npm package dependencies: `@modelcontextprotocol/sdk` and `zod`.
- Python runtime: Python 3 is required for Hermes bridge calls and `hermesctl`.
- Hermes runtime: the bridge can use `HERMES_BRIDGE_COMMAND`, `HERMES_PYTHON`,
  or the default Hermes runtime under `HERMES_HOME`.

## Distribution shape

The package is published as `@destruction13/hermes-overlord-mcp` with the binary
`hermes-overlord-mcp`. The generated portable template includes only sanitized
runtime profiles, selected skills, client config snippets, docs, and source
needed by the MCP bridge.

## Evidence

- `package.json`
- `bin/hermes-overlord-mcp.js`
- `hermesctl.py`
- `mcp/hermes_overlord_mcp.py`
- `docs/distribution/README.md`
