# Hermes Overlord MCP distribution

Hermes Overlord ships as one MCP server and a set of config generators. The
server is universal; the generated config is the small adapter that each IDE or
agent client needs because clients store MCP settings in different files.

## Quick start

Use the public GitHub package before npm publication:

```bash
npx -y github:Destruction13/hermes-overlord-mcp install
npx -y github:Destruction13/hermes-overlord-mcp init --client generic
npx -y github:Destruction13/hermes-overlord-mcp doctor
```

The `install` command prints the same kind of setup surface many MCP products
show in their docs: a standard JSON block, requirements, and per-client setup
blocks.

For a static copy of that install surface, see
[`INSTALL.md`](./INSTALL.md).

Use npm after publication:

```bash
npx -y @destruction13/hermes-overlord-mcp install
npx -y @destruction13/hermes-overlord-mcp init --client generic
npx -y @destruction13/hermes-overlord-mcp doctor
```

Generate snippets for specific clients when you know the target IDE:

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client generic
npx -y github:Destruction13/hermes-overlord-mcp config --client claude-code
npx -y github:Destruction13/hermes-overlord-mcp config --client codex
npx -y github:Destruction13/hermes-overlord-mcp config --client vscode
npx -y github:Destruction13/hermes-overlord-mcp config --client cursor
npx -y github:Destruction13/hermes-overlord-mcp config --client windsurf
npx -y github:Destruction13/hermes-overlord-mcp config --client opencode
npx -y github:Destruction13/hermes-overlord-mcp config --client gemini-cli
npx -y github:Destruction13/hermes-overlord-mcp config --client kilo
npx -y github:Destruction13/hermes-overlord-mcp config --client kiro
npx -y github:Destruction13/hermes-overlord-mcp config --client antigravity
npx -y github:Destruction13/hermes-overlord-mcp config --client cline
npx -y github:Destruction13/hermes-overlord-mcp config --client roo-code
npx -y github:Destruction13/hermes-overlord-mcp config --client continue
npx -y github:Destruction13/hermes-overlord-mcp config --client zed
```

When you use the GitHub install path, `npx` passes that package reference
through to generated configs. The resulting client config keeps
`github:Destruction13/hermes-overlord-mcp` as the launch target.

VS Code-style clients that support `--add-mcp` can consume the flat payload from
the `add-mcp` format:

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client kiro --format add-mcp
npx -y github:Destruction13/hermes-overlord-mcp config --client antigravity --format add-mcp
npx -y github:Destruction13/hermes-overlord-mcp config --client vscode --format add-mcp
npx -y github:Destruction13/hermes-overlord-mcp config --client cursor --format add-mcp
```

## Runtime contract

Hermes is exposed through one MCP server:

- Server id: `hermes-overlord`.
- Display name: `Hermes Overlord`.
- Local transport: `stdio`, launched by `npx`.
- Optional transport: Streamable HTTP at `http://127.0.0.1:8765/mcp`.

The client submits one durable root task with `hermes_submit_task`, then checks
`hermes_task_report`, `hermes_task_status`, or `hermes_task_events`. The client
is the gateway and curator. Hermes owns routing, specialist profiles, souls,
Kanban delegation, MCP/tool usage, review, watchdog, and final synthesis.

## Required environment

Credentials are never bundled. Configure secrets in the user's shell, IDE
secret store, or MCP client environment.

Common environment variables:

- `HERMES_HOME`: Hermes runtime home. Defaults to `%LOCALAPPDATA%\hermes` on
  Windows and `~/.hermes` on macOS/Linux.
- `HERMES_PYTHON`: Optional explicit Python interpreter.
- `HERMES_BRIDGE_COMMAND`: Optional full command override for unusual installs.
- `HERMES_BRIDGE_BOARD`: Defaults to `overlord`.
- `HERMES_BRIDGE_PROFILE`: Defaults to `overlord`.
- `HERMES_BRIDGE_WORKSPACE`: Default workspace for submitted tasks.

Each exported profile has an `ENV_KEYS.txt` file that lists the environment
variable names it expects. Those files contain names only, not secret values.

## Included

The portable package includes the parts needed to recreate a clean Hermes MCP
contour:

- MCP and bridge source code.
- Node `bin` launcher for `npx`.
- Dashboard source without generated screenshots or local build artifacts.
- Sanitized `SOUL.md`, `profile.yaml`, `config.template.yaml`, and
  `ENV_KEYS.txt` files for `overlord` and `ol*` profiles.
- Selected skills needed to understand, audit, and extend the package.
- Config snippets for generic MCP, Claude Code, Codex, VS Code, Cursor,
  Windsurf, OpenCode, Gemini CLI, Kilo, Kiro, Antigravity, Cline, Roo Code,
  Continue, and Zed.
- Flat `add-mcp` payloads for VS Code, Cursor, Kiro, and Antigravity CLI
  installs.
- A generated `client-configs/INSTALL.md` guide with standard and
  client-specific snippets.
- Distribution docs and a machine-readable `MANIFEST.json` in generated builds.

## Excluded

The package excludes local state and sensitive data:

- `.env`, auth files, OAuth caches, token stores, and raw secrets.
- Kanban databases, task history, worker logs, sessions, memories, and caches.
- `node_modules`, local virtual environments, and downloaded archives.
- `scratch/`, smoke-test outputs, old diagnostic handoff bundles.
- Python bytecode, backups, generated screenshots, and dashboard previews.

## Cleanup flow

Audit first:

```bash
python hermesctl.py clean-audit
```

Quarantine after reviewing the manifest:

```bash
python hermesctl.py clean-audit --quarantine
```

The command writes `cleanup-manifest.json` and moves confirmed non-shareable
artifacts to a sibling `Hermes-quarantine-YYYYMMDD-HHMMSS` directory.

## Troubleshooting

If MCP tools do not list, run:

```bash
npx -y @destruction13/hermes-overlord-mcp doctor
```

Then check these items:

- Confirm that Python 3 is installed or set `HERMES_PYTHON`.
- Confirm that `HERMES_HOME` points to the intended runtime home.
- Confirm that profile secrets named in `ENV_KEYS.txt` are configured.
- Use `stdio` first when an IDE has trouble with HTTP.
- Keep Streamable HTTP on `127.0.0.1` unless you add explicit remote
  authentication and network controls.
