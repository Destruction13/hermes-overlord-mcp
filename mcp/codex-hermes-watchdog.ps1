param(
    [int]$IntervalSeconds = 60,
    [int]$TimeoutSeconds = 90,
    [switch]$Quiet
)

$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$HermesHome = Join-Path $env:LOCALAPPDATA "hermes"
$LogDir = Join-Path $HermesHome "logs"
$LogPath = Join-Path $LogDir "codex-hermes-watchdog.log"
$StatePath = Join-Path $LogDir "codex-hermes-watchdog-state.json"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-WatchdogLog {
    param([string]$Message)
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
    if (-not $Quiet) { Write-Output $Message }
}

function Read-State {
    if (-not (Test-Path -LiteralPath $StatePath)) { return @{} }
    try {
        $raw = Get-Content -LiteralPath $StatePath -Raw -ErrorAction Stop
        if (-not $raw.Trim()) { return @{} }
        $obj = $raw | ConvertFrom-Json -ErrorAction Stop
        $hash = @{}
        foreach ($prop in $obj.PSObject.Properties) { $hash[$prop.Name] = $prop.Value }
        return $hash
    } catch {
        return @{}
    }
}

function Write-State {
    param([hashtable]$State)
    $State | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $StatePath -Encoding UTF8
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

$createdNew = $false
$mutex = [System.Threading.Mutex]::new($false, "Local\HermesCodexMcpWatchdog", [ref]$createdNew)
if (-not $mutex.WaitOne(0)) {
    Write-WatchdogLog "another watchdog instance is already running"
    exit 0
}

try {
    Write-WatchdogLog "watchdog started pid=$PID interval=${IntervalSeconds}s"
    while ($true) {
        $state = Read-State
        $now = Get-Date
        $previousStatus = "unknown"
        if ($state.ContainsKey("status") -and $null -ne $state["status"]) {
            $previousStatus = [string]$state["status"]
        }
        $consecutiveFailures = 0
        if ($state.ContainsKey("consecutiveFailures") -and $null -ne $state["consecutiveFailures"]) {
            $consecutiveFailures = [int]$state["consecutiveFailures"]
        }

        try {
            if (-not (Test-PortOpen -HostName "127.0.0.1" -Port 8765)) {
                Write-WatchdogLog "MCP HTTP port is down; starting service"
                Start-Process -FilePath "powershell.exe" -ArgumentList @(
                    "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", (Join-Path $Root "mcp\run-hermes-overlord-mcp-http.ps1")
                ) -WindowStyle Hidden | Out-Null
                Start-Sleep -Seconds 5
            }

            & (Join-Path $Root "mcp\codex-hermes-preflight.ps1") -Quiet -TimeoutSeconds $TimeoutSeconds
            $code = $LASTEXITCODE
            if ($code -eq 0) {
                $state["status"] = "ok"
                $state["lastOk"] = $now.ToString("o")
                $state["consecutiveFailures"] = 0
                if ($previousStatus -ne "ok") {
                    Write-WatchdogLog "health recovered"
                }
            } else {
                $consecutiveFailures += 1
                $state["status"] = "failed"
                $state["lastFailure"] = $now.ToString("o")
                $state["consecutiveFailures"] = $consecutiveFailures
                Write-WatchdogLog "preflight failed exit=$code consecutiveFailures=$consecutiveFailures"
            }
        } catch {
            $consecutiveFailures += 1
            $state["status"] = "failed"
            $state["lastFailure"] = $now.ToString("o")
            $state["consecutiveFailures"] = $consecutiveFailures
            $state["lastError"] = $_.Exception.Message
            Write-WatchdogLog ("watchdog check failed: " + $_.Exception.Message)
        }

        $state["lastHeartbeat"] = (Get-Date).ToString("o")
        Write-State -State $state
        Start-Sleep -Seconds ([Math]::Max(10, $IntervalSeconds))
    }
} finally {
    try { $mutex.ReleaseMutex() | Out-Null } catch {}
    $mutex.Dispose()
}
