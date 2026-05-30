param(
    [switch]$Quiet,
    [int]$TimeoutSeconds = 90
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$HermesHome = Join-Path $env:LOCALAPPDATA "hermes"
$Python = Join-Path $HermesHome "hermes-agent\venv\Scripts\python.exe"
$LogDir = Join-Path $HermesHome "logs"
$LogPath = Join-Path $LogDir "codex-hermes-mcp-preflight.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-PreflightLog {
    param([string]$Message)
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
    if (-not $Quiet) { Write-Output $Message }
}

function Test-PortOpen {
    param([string]$HostName, [int]$Port)
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $iar = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $iar.AsyncWaitHandle.WaitOne(500)) { return $false }
        $client.EndConnect($iar)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

try {
    if (-not (Test-Path -LiteralPath $Python)) {
        throw "Hermes Python runtime not found: $Python"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $Root "mcp\hermes_overlord_mcp.py"))) {
        throw "Hermes Overlord MCP bridge not found under $Root\mcp"
    }

    Write-PreflightLog "checking py_compile"
    & $Python -m py_compile (Join-Path $Root "mcp\hermes_overlord_mcp.py")
    if ($LASTEXITCODE -ne 0) { throw "py_compile failed for hermes_overlord_mcp.py" }
    & $Python -m py_compile (Join-Path $Root "mcp\codex_hermes_cli.py")
    if ($LASTEXITCODE -ne 0) { throw "py_compile failed for codex_hermes_cli.py" }

    $env:HERMES_HOME = $HermesHome
    $env:HERMES_OVERLORD_ROOT = $Root
    $env:HERMES_OVERLORD_BOARD = "overlord"
    $env:HERMES_OVERLORD_WORKSPACE = "dir:C:\AI"
    $env:HERMES_OVERLORD_ASSIGNEE = "overlord"
    $env:HERMES_OVERLORD_TIMEOUT = "180"
    $env:HERMES_QUIET = "1"
    $env:HERMES_REDACT_SECRETS = "true"
    $env:HERMES_OVERLORD_MCP_TRANSPORT = "streamable-http"
    $env:HERMES_OVERLORD_MCP_HOST = "127.0.0.1"
    $env:HERMES_OVERLORD_MCP_PORT = "8765"
    $env:HERMES_OVERLORD_MCP_PATH = "/mcp"
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"

    $startHttp = Join-Path $Root "mcp\run-hermes-overlord-mcp-http.ps1"
    if (Test-Path -LiteralPath $startHttp) {
        if (-not (Test-PortOpen -HostName "127.0.0.1" -Port 8765)) {
            Write-PreflightLog "starting Hermes Overlord HTTP MCP service"
            Start-Process -FilePath "powershell.exe" -ArgumentList @(
                "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $startHttp
            ) -WindowStyle Hidden | Out-Null
            $deadline = (Get-Date).AddSeconds(20)
            while ((Get-Date) -lt $deadline) {
                if (Test-PortOpen -HostName "127.0.0.1" -Port 8765) { break }
                Start-Sleep -Milliseconds 500
            }
        } else {
            Write-PreflightLog "Hermes Overlord HTTP MCP service already listening"
        }
    }

    $probe = @'
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client


async def list_tools(name, command, args, timeout):
    env = dict(os.environ)
    env["HERMES_OVERLORD_MCP_TRANSPORT"] = "stdio"
    params = StdioServerParameters(command=command, args=args, env=env)

    async def run_probe():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                return sorted(tool.name for tool in tools.tools)

    tools = await asyncio.wait_for(run_probe(), timeout=timeout)
    return {"name": name, "tool_count": len(tools), "tools": tools}


async def list_tools_http(name, url, timeout):
    async def run_probe():
        async with streamablehttp_client(url, timeout=timeout) as (read, write, _get_session_id):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                return sorted(tool.name for tool in tools.tools)

    tools = await asyncio.wait_for(run_probe(), timeout=timeout)
    return {"name": name, "url": url, "tool_count": len(tools), "tools": tools}


async def main():
    root = os.environ["HERMES_OVERLORD_ROOT"]
    home = os.environ["HERMES_HOME"]
    python = os.path.join(home, "hermes-agent", "venv", "Scripts", "python.exe")
    timeout = int(os.environ.get("CODEX_HERMES_PREFLIGHT_TIMEOUT", "90"))

    results = []
    results.append(await list_tools_http(
        "hermes-overlord-http",
        "http://127.0.0.1:8765/mcp",
        timeout,
    ))
    results.append(await list_tools(
        "hermes-overlord-stdio",
        python,
        [os.path.join(root, "mcp", "hermes_overlord_mcp.py")],
        timeout,
    ))
    results.append(await list_tools(
        "hermes-conversations",
        "powershell.exe",
        ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(root, "overlord.ps1"), "mcp", "serve"],
        timeout,
    ))
    print(json.dumps(results, ensure_ascii=False))


asyncio.run(main())
'@

    $env:CODEX_HERMES_PREFLIGHT_TIMEOUT = [string]$TimeoutSeconds
    Write-PreflightLog "checking Codex Hermes MCP stdio bridges"
    $probeErrPath = Join-Path $LogDir "codex-hermes-mcp-preflight-probe.stderr.log"
    $oldErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -Scope Global -ErrorAction SilentlyContinue) {
        $global:PSNativeCommandUseErrorActionPreference = $false
    }
    $probeOutput = $probe | & $Python - 2> $probeErrPath
    $probeExitCode = $LASTEXITCODE
    $ErrorActionPreference = $oldErrorActionPreference
    if ($probeExitCode -ne 0) {
        $probeErr = ""
        if (Test-Path -LiteralPath $probeErrPath) {
            $probeErr = (Get-Content -LiteralPath $probeErrPath -Raw -ErrorAction SilentlyContinue)
        }
        throw ("MCP probe failed: " + ($probeErr.Trim() | Select-Object -First 1))
    }
    Write-PreflightLog "mcp probe ok: $probeOutput"

    Write-PreflightLog "checking Hermes gateway"
    $gatewayStatus = & (Join-Path $Root "overlord.ps1") gateway status 2>&1 | Out-String
    if ($gatewayStatus -notmatch "Gateway process running") {
        Write-PreflightLog "gateway not running; restarting"
        & (Join-Path $Root "overlord.ps1") gateway restart | Out-Null
    } else {
        Write-PreflightLog "gateway ok"
    }

    Write-PreflightLog "preflight ok"
    exit 0
} catch {
    Write-PreflightLog ("preflight failed: " + $_.Exception.Message)
    exit 1
}
