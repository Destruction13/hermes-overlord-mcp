param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 9119,
    [switch]$Open
)

$ErrorActionPreference = "Stop"

$Url = "http://$HostName`:$Port/kanban?board=overlord"

try {
    Invoke-WebRequest -UseBasicParsing -Uri "http://$HostName`:$Port" -TimeoutSec 3 | Out-Null
    Write-Host "Overlord dashboard is already running: $Url"
} catch {
    $ArgsForDashboard = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", (Join-Path $PSScriptRoot "overlord.ps1"),
        "dashboard",
        "--host", $HostName,
        "--port", $Port,
        "--no-open"
    )

    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList $ArgsForDashboard -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 2
    Write-Host "Started Overlord dashboard process PID=$($proc.Id)"
    Write-Host "Open: $Url"
}

if ($Open) {
    Start-Process $Url
}
