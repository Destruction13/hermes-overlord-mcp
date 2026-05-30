param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8787,
    [switch]$Open
)

$ErrorActionPreference = "Stop"

$env:HERMES_SITE_HOST = $HostName
$env:HERMES_SITE_PORT = [string]$Port
$Url = "http://$HostName`:$Port/"

try {
    Invoke-WebRequest -UseBasicParsing -Uri "http://$HostName`:$Port/api/live/health" -TimeoutSec 2 | Out-Null
    Write-Host "Hermes site is already running: $Url"
} catch {
    $Script = Join-Path $PSScriptRoot "dashboard\serve-dashboard.py"
    $proc = Start-Process -FilePath "python" -ArgumentList @($Script) -WorkingDirectory (Join-Path $PSScriptRoot "dashboard") -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 2
    Write-Host "Started Hermes site process PID=$($proc.Id)"
    Write-Host "Open: $Url"
}

if ($Open) {
    Start-Process $Url
}
