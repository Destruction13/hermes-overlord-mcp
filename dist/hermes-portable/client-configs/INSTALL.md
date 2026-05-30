# Install Hermes Overlord MCP

## Standard configuration for most tools

Use this JSON when your client accepts a normal `mcpServers` object:

```json
{
  "mcpServers": {
    "hermes-overlord": {
      "command": "npx",
      "args": [
        "-y",
        "github:Destruction13/hermes-overlord-mcp"
      ],
      "env": {
        "HERMES_HOME": "${HERMES_HOME}",
        "HERMES_BRIDGE_PROFILE": "overlord",
        "HERMES_BRIDGE_BOARD": "overlord",
        "HERMES_BRIDGE_WORKSPACE": "dir:${HERMES_WORKSPACE_ROOT}",
        "HERMES_BRIDGE_CLIENT": "generic"
      }
    }
  }
}
```

## Requirements

- Node.js 20 or newer
- Python 3
- An MCP-compatible client

## Client-specific configuration

Each client stores MCP settings differently. The server stays the same; only this adapter changes.

<details open>
<summary>Claude Code</summary>

Config location: `Claude Code local project scope or .mcp.json`.

```bash
claude mcp add hermes-overlord --scope local -e HERMES_BRIDGE_CLIENT=claude-code -- npx -y github:Destruction13/hermes-overlord-mcp
```

</details>

<details>
<summary>Codex</summary>

Config location: `~/.codex/config.toml through codex mcp add`.

```bash
codex mcp add hermes-overlord --env HERMES_BRIDGE_CLIENT=codex -- npx -y github:Destruction13/hermes-overlord-mcp
```

</details>

<details>
<summary>VS Code / GitHub Copilot</summary>

Config location: `.vscode/mcp.json or VS Code user MCP settings`.

Generate the flat add-mcp payload:

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client vscode --format add-mcp
```

Payload:

```json
{
  "name": "hermes-overlord",
  "command": "npx",
  "args": [
    "-y",
    "github:Destruction13/hermes-overlord-mcp"
  ],
  "env": {
    "HERMES_HOME": "${HERMES_HOME}",
    "HERMES_BRIDGE_PROFILE": "overlord",
    "HERMES_BRIDGE_BOARD": "overlord",
    "HERMES_BRIDGE_WORKSPACE": "dir:${HERMES_WORKSPACE_ROOT}",
    "HERMES_BRIDGE_CLIENT": "vscode"
  }
}
```

</details>

<details>
<summary>Cursor</summary>

Config location: `Cursor MCP settings or project mcp.json`.

Generate the flat add-mcp payload:

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client cursor --format add-mcp
```

Payload:

```json
{
  "name": "hermes-overlord",
  "command": "npx",
  "args": [
    "-y",
    "github:Destruction13/hermes-overlord-mcp"
  ],
  "env": {
    "HERMES_HOME": "${HERMES_HOME}",
    "HERMES_BRIDGE_PROFILE": "overlord",
    "HERMES_BRIDGE_BOARD": "overlord",
    "HERMES_BRIDGE_WORKSPACE": "dir:${HERMES_WORKSPACE_ROOT}",
    "HERMES_BRIDGE_CLIENT": "cursor"
  }
}
```

</details>

<details>
<summary>Windsurf</summary>

Config location: `Windsurf Cascade MCP settings`.

Generate the client config snippet:

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client windsurf
```

Snippet:

```json
{
  "mcpServers": {
    "hermes-overlord": {
      "command": "npx",
      "args": [
        "-y",
        "github:Destruction13/hermes-overlord-mcp"
      ],
      "env": {
        "HERMES_HOME": "${HERMES_HOME}",
        "HERMES_BRIDGE_PROFILE": "overlord",
        "HERMES_BRIDGE_BOARD": "overlord",
        "HERMES_BRIDGE_WORKSPACE": "dir:${HERMES_WORKSPACE_ROOT}",
        "HERMES_BRIDGE_CLIENT": "windsurf"
      }
    }
  }
}
```

</details>

<details>
<summary>OpenCode</summary>

Config location: `opencode.json`.

Generate the client config snippet:

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client opencode
```

Snippet:

```json
{
  "mcp": {
    "hermes-overlord": {
      "type": "local",
      "command": [
        "npx",
        "-y",
        "github:Destruction13/hermes-overlord-mcp"
      ],
      "environment": {
        "HERMES_HOME": "${HERMES_HOME}",
        "HERMES_BRIDGE_PROFILE": "overlord",
        "HERMES_BRIDGE_BOARD": "overlord",
        "HERMES_BRIDGE_WORKSPACE": "dir:${HERMES_WORKSPACE_ROOT}",
        "HERMES_BRIDGE_CLIENT": "opencode"
      },
      "enabled": true
    }
  }
}
```

</details>

<details>
<summary>Gemini CLI</summary>

Config location: `~/.gemini/settings.json`.

Generate the client config snippet:

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client gemini-cli
```

Snippet:

```json
{
  "mcpServers": {
    "hermes-overlord": {
      "command": "npx",
      "args": [
        "-y",
        "github:Destruction13/hermes-overlord-mcp"
      ],
      "env": {
        "HERMES_HOME": "${HERMES_HOME}",
        "HERMES_BRIDGE_PROFILE": "overlord",
        "HERMES_BRIDGE_BOARD": "overlord",
        "HERMES_BRIDGE_WORKSPACE": "dir:${HERMES_WORKSPACE_ROOT}",
        "HERMES_BRIDGE_CLIENT": "gemini-cli"
      }
    }
  }
}
```

</details>

<details>
<summary>Kilo Code</summary>

Config location: `Kilo Code MCP settings`.

Generate the client config snippet:

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client kilo
```

Snippet:

```json
{
  "mcpServers": {
    "hermes-overlord": {
      "command": "npx",
      "args": [
        "-y",
        "github:Destruction13/hermes-overlord-mcp"
      ],
      "env": {
        "HERMES_HOME": "${HERMES_HOME}",
        "HERMES_BRIDGE_PROFILE": "overlord",
        "HERMES_BRIDGE_BOARD": "overlord",
        "HERMES_BRIDGE_WORKSPACE": "dir:${HERMES_WORKSPACE_ROOT}",
        "HERMES_BRIDGE_CLIENT": "kilo"
      }
    }
  }
}
```

</details>

<details>
<summary>Kiro</summary>

Config location: `.kiro/settings/mcp.json or Kiro user MCP settings`.

Generate the flat add-mcp payload:

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client kiro --format add-mcp
```

Payload:

```json
{
  "name": "hermes-overlord",
  "command": "npx",
  "args": [
    "-y",
    "github:Destruction13/hermes-overlord-mcp"
  ],
  "env": {
    "HERMES_HOME": "${HERMES_HOME}",
    "HERMES_BRIDGE_PROFILE": "overlord",
    "HERMES_BRIDGE_BOARD": "overlord",
    "HERMES_BRIDGE_WORKSPACE": "dir:${HERMES_WORKSPACE_ROOT}",
    "HERMES_BRIDGE_CLIENT": "kiro"
  }
}
```

</details>

<details>
<summary>Antigravity</summary>

Config location: `~/.gemini/antigravity/mcp_config.json or plugin mcp_config.json`.

Generate the flat add-mcp payload:

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client antigravity --format add-mcp
```

Payload:

```json
{
  "name": "hermes-overlord",
  "command": "npx",
  "args": [
    "-y",
    "github:Destruction13/hermes-overlord-mcp"
  ],
  "env": {
    "HERMES_HOME": "${HERMES_HOME}",
    "HERMES_BRIDGE_PROFILE": "overlord",
    "HERMES_BRIDGE_BOARD": "overlord",
    "HERMES_BRIDGE_WORKSPACE": "dir:${HERMES_WORKSPACE_ROOT}",
    "HERMES_BRIDGE_CLIENT": "antigravity"
  }
}
```

</details>

<details>
<summary>Cline</summary>

Config location: `Cline MCP settings`.

Generate the client config snippet:

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client cline
```

Snippet:

```json
{
  "mcpServers": {
    "hermes-overlord": {
      "command": "npx",
      "args": [
        "-y",
        "github:Destruction13/hermes-overlord-mcp"
      ],
      "env": {
        "HERMES_HOME": "${HERMES_HOME}",
        "HERMES_BRIDGE_PROFILE": "overlord",
        "HERMES_BRIDGE_BOARD": "overlord",
        "HERMES_BRIDGE_WORKSPACE": "dir:${HERMES_WORKSPACE_ROOT}",
        "HERMES_BRIDGE_CLIENT": "cline"
      }
    }
  }
}
```

</details>

<details>
<summary>Roo Code</summary>

Config location: `Roo Code MCP settings`.

Generate the client config snippet:

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client roo-code
```

Snippet:

```json
{
  "mcpServers": {
    "hermes-overlord": {
      "command": "npx",
      "args": [
        "-y",
        "github:Destruction13/hermes-overlord-mcp"
      ],
      "env": {
        "HERMES_HOME": "${HERMES_HOME}",
        "HERMES_BRIDGE_PROFILE": "overlord",
        "HERMES_BRIDGE_BOARD": "overlord",
        "HERMES_BRIDGE_WORKSPACE": "dir:${HERMES_WORKSPACE_ROOT}",
        "HERMES_BRIDGE_CLIENT": "roo-code"
      }
    }
  }
}
```

</details>

<details>
<summary>Continue</summary>

Config location: `.continue config or MCP server settings`.

Generate the client config snippet:

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client continue
```

Snippet:

```json
{
  "mcpServers": {
    "hermes-overlord": {
      "command": "npx",
      "args": [
        "-y",
        "github:Destruction13/hermes-overlord-mcp"
      ],
      "env": {
        "HERMES_HOME": "${HERMES_HOME}",
        "HERMES_BRIDGE_PROFILE": "overlord",
        "HERMES_BRIDGE_BOARD": "overlord",
        "HERMES_BRIDGE_WORKSPACE": "dir:${HERMES_WORKSPACE_ROOT}",
        "HERMES_BRIDGE_CLIENT": "continue"
      }
    }
  }
}
```

</details>

<details>
<summary>Zed</summary>

Config location: `Zed settings.json context_servers`.

Generate the client config snippet:

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client zed
```

Snippet:

```json
{
  "context_servers": {
    "hermes-overlord": {
      "source": "custom",
      "command": {
        "path": "npx",
        "args": [
          "-y",
          "github:Destruction13/hermes-overlord-mcp"
        ],
        "env": {
          "HERMES_HOME": "${HERMES_HOME}",
          "HERMES_BRIDGE_PROFILE": "overlord",
          "HERMES_BRIDGE_BOARD": "overlord",
          "HERMES_BRIDGE_WORKSPACE": "dir:${HERMES_WORKSPACE_ROOT}",
          "HERMES_BRIDGE_CLIENT": "zed"
        }
      }
    }
  }
}
```

</details>

## Health check

```bash
npx -y github:Destruction13/hermes-overlord-mcp doctor
```
