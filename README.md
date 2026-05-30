# Hermes Overlord MCP

Hermes Overlord MCP is a client-neutral MCP server for the Hermes Overlord
agent contour. It exposes one portable MCP surface that any MCP-compatible IDE
or agent client can launch with `npx`, then use through standard MCP tools.

The server id is `hermes-overlord`. The display name is `Hermes Overlord`.

## Quick start

Install or run Hermes from the public GitHub package with `npx`:

```bash
npx -y github:Destruction13/hermes-overlord-mcp install
npx -y github:Destruction13/hermes-overlord-mcp init --client generic
npx -y github:Destruction13/hermes-overlord-mcp doctor
```

The `install` command prints a screenshot-style guide: standard JSON for most
MCP clients, requirements, and client-specific snippets for Claude Code, Codex,
VS Code, Cursor, Windsurf, OpenCode, Gemini CLI, Kilo, Kiro, Antigravity,
Cline, Roo Code, Continue, and Zed.

After the package is published to npm, use the package name directly:

```bash
npx -y @destruction13/hermes-overlord-mcp install
npx -y @destruction13/hermes-overlord-mcp init --client generic
npx -y @destruction13/hermes-overlord-mcp doctor
```

For any MCP client that supports local `stdio` servers, the core launch command
is:

```json
{
  "mcpServers": {
    "hermes-overlord": {
      "command": "npx",
      "args": ["-y", "github:Destruction13/hermes-overlord-mcp"],
      "env": {
        "HERMES_BRIDGE_CLIENT": "generic"
      }
    }
  }
}
```

Use `config` to generate client-specific snippets:

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

For Claude Code and Codex, `install --client` prints the direct CLI command:

```bash
npx -y github:Destruction13/hermes-overlord-mcp install --client claude-code
npx -y github:Destruction13/hermes-overlord-mcp install --client codex
```

VS Code-style clients that expose `--add-mcp`, including VS Code, Cursor, Kiro,
and Antigravity, can use the flat install payload:

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client kiro --format add-mcp
```

## What the MCP exposes

Hermes Overlord MCP lists these tools:

- `hermes_submit_task`
- `hermes_task_report`
- `hermes_task_status`
- `hermes_task_events`
- `hermes_heartbeat_prompt`
- `hermes_task_list`
- `hermes_task_comment`
- `hermes_task_log`
- `hermes_dispatch_once`
- `hermes_gateway_status`
- `hermes_autocheck`
- `hermes_direct_ask`

The client submits one durable root task. Hermes owns routing, specialist
profiles, skills, MCP/tool usage, review, watchdog, and synthesis.

## Commands

```bash
hermes-overlord-mcp                 # start MCP over stdio
hermes-overlord-mcp init            # create HERMES_HOME templates and config
hermes-overlord-mcp install         # print install guide/client snippets
hermes-overlord-mcp config          # print MCP config JSON
hermes-overlord-mcp doctor          # check local readiness
hermes-overlord-mcp start-http      # start Streamable HTTP on localhost
hermes-overlord-mcp package         # build dist/hermes-portable
hermes-overlord-mcp clean-audit     # audit non-shareable local files
```

`stdio` is the default for local IDEs. Streamable HTTP is available for local or
remote gateways:

```bash
npx -y github:Destruction13/hermes-overlord-mcp start-http --host 127.0.0.1 --port 8765
```

Remote HTTP exposure must add explicit authentication and network controls.

## Runtime environment

The package never bundles credentials. Configure secrets through environment
variables, shell profiles, IDE secret storage, or your MCP client environment.

Common environment variables:

- `HERMES_HOME`: Hermes runtime home. Defaults to `%LOCALAPPDATA%\hermes` on
  Windows and `~/.hermes` on macOS/Linux.
- `HERMES_PYTHON`: Optional explicit Python interpreter.
- `HERMES_BRIDGE_COMMAND`: Optional full command override for unusual runtime
  installs.
- `HERMES_BRIDGE_BOARD`: Defaults to `overlord`.
- `HERMES_BRIDGE_PROFILE`: Defaults to `overlord`.
- `HERMES_BRIDGE_WORKSPACE`: Default workspace for submitted tasks.

## Development

Build and check the portable template:

```bash
python hermesctl.py package
python hermesctl.py doctor
python -m unittest discover -s tests
npm pack --dry-run
```

The portable template intentionally excludes secrets, token caches, Kanban
history, logs, sessions, screenshots, scratch workspaces, `node_modules`, and
Python bytecode. See `docs/distribution/README.md` for the distribution guide.

Codex-specific `/hermes` guardrails remain separate from the universal MCP
package. The MCP server itself is not tied to Codex, Antigravity, or any single
IDE.
