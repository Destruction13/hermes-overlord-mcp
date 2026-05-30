param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8765,
    [string]$Path = "/mcp",
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$HermesHome = Join-Path $env:LOCALAPPDATA "hermes"
$Python = Join-Path $HermesHome "hermes-agent\venv\Scripts\python.exe"
$LogDir = Join-Path $HermesHome "logs"
$StdoutLog = Join-Path $LogDir "hermes-overlord-mcp-http.stdout.log"
$StderrLog = Join-Path $LogDir "hermes-overlord-mcp-http.stderr.log"
$LifecycleLog = Join-Path $LogDir "hermes-overlord-mcp-http.lifecycle.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-LifeLog {
    param([string]$Message)
    Add-Content -LiteralPath $LifecycleLog -Value ("{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message) -Encoding UTF8
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

    if (Test-PortOpen -HostName $HostName -Port $Port) {
        Write-LifeLog "port $HostName`:$Port is already listening; leaving existing MCP service in place"
        exit 0
    }

    $env:HERMES_HOME = $HermesHome
    $env:HERMES_OVERLORD_ROOT = $Root
    $env:HERMES_OVERLORD_BOARD = "overlord"
    $env:HERMES_OVERLORD_WORKSPACE = "dir:C:\AI"
    $env:HERMES_OVERLORD_ASSIGNEE = "overlord"
    $env:HERMES_OVERLORD_TIMEOUT = "180"
    $env:HERMES_QUIET = "1"
    $env:HERMES_REDACT_SECRETS = "true"
    $env:HERMES_OVERLORD_MCP_TRANSPORT = "streamable-http"
    $env:HERMES_OVERLORD_MCP_HOST = $HostName
    $env:HERMES_OVERLORD_MCP_PORT = [string]$Port
    $env:HERMES_OVERLORD_MCP_PATH = $Path
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"

    Set-Location -LiteralPath $Root
    Write-LifeLog "starting hermes-overlord MCP HTTP service on http://$HostName`:$Port$Path"
    $oldErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -Scope Global -ErrorAction SilentlyContinue) {
        $global:PSNativeCommandUseErrorActionPreference = $false
    }
    & $Python (Join-Path $Root "mcp\hermes_overlord_mcp.py") 1>> $StdoutLog 2>> $StderrLog
    $code = $LASTEXITCODE
    $ErrorActionPreference = $oldErrorActionPreference
    Write-LifeLog "MCP HTTP service exited with code $code"
    exit $code
} catch {
    Write-LifeLog ("MCP HTTP service failed before start: " + $_.Exception.Message)
    exit 1
}
