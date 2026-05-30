# Structure

## Root layout

- `bin/`: Node `npx` launcher and primary MCP server entrypoint.
- `bridge/`: Python bridge shared by the MCP tools and CLI wrappers.
- `mcp/`: optional Python MCP adapter plus legacy client-specific reliability
  scripts.
- `dashboard/`: dashboard source and local development server.
- `docs/`: distribution guide, codebase map, and operational notes.
- `dist/hermes-portable/`: generated sanitized portable template.
- `skills/`: local skill mirror; the published package includes only selected
  Hermes skills.
- `tests/`: Python tests for bridge, packaging, cleanup, and config generation.
- `hermesctl.py`: package, init, doctor, cleanup, and config utility.

## Runtime profile layout

Runtime state is not stored in the package by default. `HERMES_HOME` points to
the user's Hermes runtime home:

- `profiles/overlord`: main Overlord profile.
- `profiles/ol*`: specialist profiles.
- `kanban/boards/overlord/kanban.db`: live board when the Hermes runtime is
  installed.
- `logs/`, `sessions/`, and `memories/`: local runtime state excluded from the
  portable package.

## Portable template layout

The generated portable template keeps only shareable files:

- `runtime/profiles/*`: sanitized `SOUL.md`, `profile.yaml`,
  `config.template.yaml`, and `ENV_KEYS.txt`.
- `client-configs/`: JSON snippets and `INSTALL.md` for supported MCP
  clients.
- `skills/`: selected skills required to understand, audit, and extend Hermes.

## Evidence

- `README.md`
- `package.json`
- `bin/hermes-overlord-mcp.js`
- `hermesctl.py`
- `docs/distribution/README.md`
