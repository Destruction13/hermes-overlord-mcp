# Testing

## Automated tests

Run the Python suite:

```bash
python -m unittest discover -s tests
```

Run package and config checks:

```bash
python hermesctl.py package
python hermesctl.py doctor
npm pack --dry-run
```

## MCP smoke tests

Use the Node MCP client from `@modelcontextprotocol/sdk` to verify that the
`stdio` server lists Hermes tools:

```bash
node bin/hermes-overlord-mcp.js --help
npx --no-install hermes-overlord-mcp config --client generic
```

Expected tools include `hermes_submit_task`, `hermes_task_report`,
`hermes_task_status`, `hermes_dispatch_once`, and `hermes_autocheck`.

## Distribution checks

Before publishing, confirm these items:

- Generated client configs are valid JSON.
- The npm tarball does not include `.env`, token files, logs, sessions,
  screenshots, caches, `scratch/`, or `node_modules/`.
- `hermes_submit_task` supports dry-run behavior through the MCP server.
- `init` writes a user-local config file and copies sanitized templates into
  `HERMES_HOME`.

## Evidence

- `tests/test_hermesctl.py`
- `tests/test_bridge_core.py`
- `bin/hermes-overlord-mcp.js`
- `package.json`
