# Install Hermes Overlord MCP

This page mirrors the install surface users expect from modern MCP packages:
one standard config for most clients, then client-specific snippets for tools
that store MCP servers differently.

## Standard configuration

Use this block in any MCP client that accepts a normal `mcpServers` object.
This is the universal fallback when the exact client is not listed below.

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

## Requirements

The client machine must have these tools installed before it starts Hermes.

- Node.js 20 or newer.
- Python 3.
- An MCP-compatible IDE or agent client with `stdio` server support.

## Client-specific configuration

Each client has a different settings file or CLI command. The server name stays
`hermes-overlord`, and the MCP tools exposed by Hermes stay the same.

<details open>
<summary>Claude Code</summary>

Use the Claude Code MCP CLI to add Hermes to the current project scope.

```bash
claude mcp add hermes-overlord --scope local -e HERMES_BRIDGE_CLIENT=claude-code -- npx -y github:Destruction13/hermes-overlord-mcp
```

</details>

<details>
<summary>Codex</summary>

Use the Codex MCP CLI to write the server entry into `~/.codex/config.toml`.

```bash
codex mcp add hermes-overlord --env HERMES_BRIDGE_CLIENT=codex -- npx -y github:Destruction13/hermes-overlord-mcp
```

</details>

<details>
<summary>VS Code, Cursor, Kiro, and Antigravity</summary>

Generate the flat `add-mcp` payload for clients that accept one.

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client vscode --format add-mcp
npx -y github:Destruction13/hermes-overlord-mcp config --client cursor --format add-mcp
npx -y github:Destruction13/hermes-overlord-mcp config --client kiro --format add-mcp
npx -y github:Destruction13/hermes-overlord-mcp config --client antigravity --format add-mcp
```

</details>

<details>
<summary>OpenCode, Windsurf, Gemini CLI, Kilo, Cline, Roo Code, Continue, and Zed</summary>

Generate the client-specific JSON and paste it into the client MCP settings.

```bash
npx -y github:Destruction13/hermes-overlord-mcp config --client opencode
npx -y github:Destruction13/hermes-overlord-mcp config --client windsurf
npx -y github:Destruction13/hermes-overlord-mcp config --client gemini-cli
npx -y github:Destruction13/hermes-overlord-mcp config --client kilo
npx -y github:Destruction13/hermes-overlord-mcp config --client cline
npx -y github:Destruction13/hermes-overlord-mcp config --client roo-code
npx -y github:Destruction13/hermes-overlord-mcp config --client continue
npx -y github:Destruction13/hermes-overlord-mcp config --client zed
```

</details>

## Generate the guide

Use the package itself to print the current install guide. This keeps README
snippets, generated portable configs, and CLI output aligned.

```bash
npx -y github:Destruction13/hermes-overlord-mcp install
npx -y github:Destruction13/hermes-overlord-mcp install --client claude-code
npx -y github:Destruction13/hermes-overlord-mcp install --client zed --format json
```

## Health check

After adding the server to a client, run the doctor check and ask the client to
list MCP tools. Hermes should appear as `hermes-overlord` with 12 tools.

```bash
npx -y github:Destruction13/hermes-overlord-mcp doctor
```
