# Concerns

## P0 / blocking concerns

- A user can list MCP tools through `npx`, but real execution still requires a
  working Hermes runtime and credentials under `HERMES_HOME` or an explicit
  `HERMES_BRIDGE_COMMAND`.
- Client config formats are not standardized across IDEs. The universal server
  is stable, but each client adapter must be checked against that client's
  current docs before a release claim.

## P1 / operational risks

- Streamable HTTP is localhost-only by default. Remote exposure needs explicit
  authentication and network controls.
- The optional Python FastMCP adapter depends on Python MCP packages. The Node
  `npx` server is the preferred portable entrypoint.
- Dashboard source is included, but dashboard runtime state depends on the
  user's local Hermes board and logs.

## P2 / maintainability gaps

- More end-to-end tests are needed for installed packages from a clean temp
  directory.
- More client-specific config fixtures are useful as IDEs change their MCP
  settings formats.

## Evidence

- `bin/hermes-overlord-mcp.js`
- `hermesctl.py`
- `docs/distribution/README.md`
