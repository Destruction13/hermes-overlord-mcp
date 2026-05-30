# Hermes Overlord MCP

<p align="center">
  <img src="docs/assets/hermes-overlord-hero.png" alt="Hermes Overlord command throne with red terminal panels" width="100%" />
</p>

<p align="center">
  <a href="https://github.com/Destruction13/hermes-overlord-mcp"><img alt="GitHub" src="https://img.shields.io/badge/GitHub-public-111827?style=for-the-badge&logo=github&logoColor=white"></a>
  <img alt="MCP compatible" src="https://img.shields.io/badge/MCP-compatible-b91c1c?style=for-the-badge">
  <img alt="Install with npx" src="https://img.shields.io/badge/install-npx-18181b?style=for-the-badge&logo=npm&logoColor=white">
  <img alt="Twelve tools" src="https://img.shields.io/badge/tools-12-7f1d1d?style=for-the-badge">
  <img alt="Transport" src="https://img.shields.io/badge/stdio%20%7C%20http-0f172a?style=for-the-badge">
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/github/license/Destruction13/hermes-overlord-mcp?style=for-the-badge"></a>
</p>

Hermes Overlord MCP is a portable Model Context Protocol gateway for the Hermes
agent contour. It gives any MCP-compatible IDE or agent client one clean server,
one install path, and the same Overlord tool surface for task submission,
status, reports, dispatch, health checks, and direct asks.

The server appears as `hermes-overlord` / `Hermes Overlord` in MCP clients.

## Install

Use the public GitHub package today. The `install` command prints the polished
client selector with the standard config, requirements, and per-client setup
blocks.

```bash
npx -y github:Destruction13/hermes-overlord-mcp install
npx -y github:Destruction13/hermes-overlord-mcp init --client generic
npx -y github:Destruction13/hermes-overlord-mcp doctor
```

After npm publication, the same commands work with the npm package name.

```bash
npx -y @destruction13/hermes-overlord-mcp install
npx -y @destruction13/hermes-overlord-mcp init --client generic
npx -y @destruction13/hermes-overlord-mcp doctor
```

## Standard config

Use this block for any MCP client that accepts a normal `mcpServers` object.
Client-specific presets below only adapt where each app stores this same server.

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

## Клиентские предустановки

Откройте блок для своей интегрированной среды разработки или клиентского
агента. Сервер MCP универсален, небольшая оболочка меняет только конфигурацию,
которую ожидает каждый клиент.

<details>
<summary><strong>Claude Code</strong></summary>

```bash
claude mcp add hermes-overlord --scope local -e HERMES_BRIDGE_CLIENT=claude-code -- npx -y github:Destruction13/hermes-overlord-mcp
```

</details>

<details>
<summary><strong>Codex</strong></summary>

```bash
codex mcp add hermes-overlord --env HERMES_BRIDGE_CLIENT=codex -- npx -y github:Destruction13/hermes-overlord-mcp
```

</details>

<details>
<summary><strong>VS Code / GitHub Copilot</strong></summary>

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client vscode --format add-mcp
```

</details>

<details>
<summary><strong>Курсор</strong></summary>

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client cursor --format add-mcp
```

</details>

<details>
<summary><strong>Виндсерфинг</strong></summary>

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client windsurf
```

</details>

<details>
<summary><strong>OpenCode</strong></summary>

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client opencode
```

</details>

<details>
<summary><strong>Gemini CLI</strong></summary>

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client gemini-cli
```

</details>

<details>
<summary><strong>Kilo Code</strong></summary>

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client kilo
```

</details>

<details>
<summary><strong>Kiro</strong></summary>

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client kiro --format add-mcp
```

</details>

<details>
<summary><strong>Антигравитация</strong></summary>

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client antigravity --format add-mcp
```

</details>

<details>
<summary><strong>Cline</strong></summary>

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client cline
```

</details>

<details>
<summary><strong>Roo Code</strong></summary>

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client roo-code
```

</details>

<details>
<summary><strong>Продолжить</strong></summary>

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client continue
```

</details>

<details>
<summary><strong>Zed</strong></summary>

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client zed
```

</details>

## Tool surface

Hermes exposes 12 MCP tools. Submit one durable root task, then read status,
reports, or events while Hermes handles routing, profiles, skills, review, and
synthesis.

| Tool | Purpose |
| --- | --- |
| `hermes_submit_task` | Submit a durable root task to Hermes Overlord. |
| `hermes_task_report` | Read a curator-friendly report for a task family. |
| `hermes_task_status` | Read the current status of one task. |
| `hermes_task_events` | Read structured task and bridge events. |
| `hermes_heartbeat_prompt` | Generate a follow-up prompt for clients that support reminders. |
| `hermes_task_list` | List Kanban tasks on a Hermes board. |
| `hermes_task_comment` | Add a curator comment to a task. |
| `hermes_task_log` | Read the tail of a worker log. |
| `hermes_dispatch_once` | Run one dispatcher pass. |
| `hermes_gateway_status` | Check Hermes gateway process status. |
| `hermes_autocheck` | Run a quiet bridge, gateway, and Kanban health check. |
| `hermes_direct_ask` | Ask Hermes a short explicit synchronous question. |

## What ships

The public package is a clean template, not a copy of local history. It includes
the pieces needed to recreate the Hermes Overlord MCP contour.

- Runtime templates:
  - sanitized `overlord` and `ol*` profile souls;
  - profile config templates;
  - `ENV_KEYS.txt` files with variable names only.
- MCP distribution:
  - Node `npx` launcher;
  - Python bridge and CLI wrappers;
  - generated client configs;
  - `stdio` and localhost Streamable HTTP support.
- Operator material:
  - dashboard source;
  - selected skills;
  - distribution docs and manifests.

It intentionally excludes local secrets, `.env` files, OAuth caches, Kanban
history, logs, sessions, screenshots, scratch workspaces, `node_modules`, and
Python bytecode.

## Runtime environment

Credentials stay user-supplied through environment variables, shell profiles,
IDE secret stores, or MCP client config. The package never bundles tokens.

| Variable | Default | Use |
| --- | --- | --- |
| `HERMES_HOME` | `%LOCALAPPDATA%\hermes` on Windows, `~/.hermes` on macOS/Linux | User-local Hermes runtime home. |
| `HERMES_PYTHON` | auto-detected | Optional Python interpreter override. |
| `HERMES_BRIDGE_COMMAND` | package bridge | Optional full bridge command override. |
| `HERMES_BRIDGE_BOARD` | `overlord` | Hermes Kanban board. |
| `HERMES_BRIDGE_PROFILE` | `overlord` | Default Hermes profile. |
| `HERMES_BRIDGE_WORKSPACE` | user home | Default workspace for submitted tasks. |

## Commands

Use the package commands directly during development or through `npx` after
installation.

```bash
hermes-overlord-mcp                 # start MCP over stdio
hermes-overlord-mcp install         # print install guide/client snippets
hermes-overlord-mcp init            # create HERMES_HOME templates and config
hermes-overlord-mcp config          # print MCP config JSON
hermes-overlord-mcp doctor          # check local readiness
hermes-overlord-mcp start-http      # start Streamable HTTP on localhost
hermes-overlord-mcp package         # build dist/hermes-portable
hermes-overlord-mcp clean-audit     # audit non-shareable local files
```

Streamable HTTP is available for local or remote gateways. Keep it on localhost
unless you add explicit authentication and network controls.

```bash
npx -y github:Destruction13/hermes-overlord-mcp start-http --host 127.0.0.1 --port 8765
```

## Development

Run these checks before publishing changes.

```bash
python hermesctl.py package
python hermesctl.py doctor
python -m unittest discover -s tests
npm pack --dry-run
```

Codex-specific `/hermes` guardrails live separately from the universal MCP
package. The MCP server itself is not tied to Codex, Antigravity, or any single
IDE.
