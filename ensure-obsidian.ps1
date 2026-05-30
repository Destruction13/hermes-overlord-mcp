param(
    [int]$WaitSeconds = 12,
    [string]$Endpoint = "http://127.0.0.1:27123/mcp/"
)

$ErrorActionPreference = "Stop"

$ObsidianExe = "C:\Program Files\Obsidian\Obsidian.exe"

if (-not (Test-Path -LiteralPath $ObsidianExe)) {
    Write-Output "Obsidian executable not found at $ObsidianExe"
    exit 0
}

$running = Get-Process -Name Obsidian -ErrorAction SilentlyContinue
if (-not $running) {
    Start-Process -FilePath $ObsidianExe -WindowStyle Hidden
    Write-Output "Started Obsidian."
} else {
    Write-Output "Obsidian already running."
}

$deadline = (Get-Date).AddSeconds($WaitSeconds)
do {
    try {
        Invoke-WebRequest -Uri $Endpoint -Method Get -TimeoutSec 3 -UseBasicParsing | Out-Null
        Write-Output "Obsidian MCP endpoint is reachable."
        exit 0
    } catch {
        $status = $_.Exception.Response.StatusCode.value__
        if ($status -eq 401 -or $status -eq 405) {
            Write-Output "Obsidian MCP endpoint is reachable and requires auth."
            exit 0
        }
        Start-Sleep -Milliseconds 500
    }
} while ((Get-Date) -lt $deadline)

Write-Output "Obsidian started, but MCP endpoint was not reachable within $WaitSeconds seconds."
exit 0
