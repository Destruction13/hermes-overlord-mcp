param(
    [string]$Endpoint = "http://127.0.0.1:6006/mcp",
    [switch]$Enable,
    [switch]$Disable
)

$ErrorActionPreference = "Stop"

$ProfileRoot = Join-Path $env:LOCALAPPDATA "hermes\profiles\olux"
$ConfigPath = Join-Path $ProfileRoot "config.yaml"

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "olux config was not found at $ConfigPath"
}

try {
    Invoke-WebRequest -UseBasicParsing -Uri $Endpoint -Method Get -TimeoutSec 3 | Out-Null
    Write-Host "Storybook MCP endpoint is reachable: $Endpoint"
} catch {
    Write-Host "Storybook MCP endpoint is not reachable yet: $Endpoint"
    if ($Enable) {
        throw "Start the target project's Storybook MCP endpoint before enabling this MCP."
    }
}

$text = Get-Content -LiteralPath $ConfigPath -Raw
$escapedEndpoint = [regex]::Escape($Endpoint)
$text = $text -replace "(?ms)(^\s{2}storybook:\r?\n\s{4}url:)\s*.+", "`$1 $Endpoint"

if ($Enable) {
    $text = $text -replace "(?ms)(^\s{2}storybook:\r?\n(?:^\s{4}.+\r?\n)+?^\s{4}enabled:)\s*false", '$1 true'
}

if ($Disable) {
    $text = $text -replace "(?ms)(^\s{2}storybook:\r?\n(?:^\s{4}.+\r?\n)+?^\s{4}enabled:)\s*true", '$1 false'
}

Set-Content -LiteralPath $ConfigPath -Value $text -Encoding UTF8
Write-Host "Storybook MCP config updated."
